import uuid
import calendar
import csv
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
import markdown
import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import *
from .forms import CATALOG, EventForm, ComponentForm, MaintenanceForm, MovementForm, RangeForm
from .access import access, events_for, role
from . import services as s
ALL = ['Gestor','Estoque','Equipe operacional']

def error(request,exc):
    messages.error(request,' '.join(exc.messages) if isinstance(exc,ValidationError) else str(exc))

def number(request,key):
    try: return int(request.POST.get(key,''))
    except (ValueError,TypeError): raise ValidationError('Informe números inteiros válidos.')

def event_visible(request,pk): return get_object_or_404(events_for(request.user),pk=pk)

def filtered_events(request):
    qs=events_for(request.user).select_related('client','manager')
    for key,lookup in [('status','status'),('manager','manager_id'),('from','release__date__gte'),('to','withdrawal__date__lte')]:
        val=request.GET.get(key)
        if val:
            try:
                if key in ['from','to']: datetime.strptime(val,'%Y-%m-%d')
                if key=='manager': int(val)
                qs=qs.filter(**{lookup:val})
            except ValueError: messages.error(request,'Filtro inválido; use datas e responsáveis válidos.')
    q=request.GET.get('q','')
    if q: qs=qs.filter(Q(name__icontains=q)|Q(client__name__icontains=q))
    return qs

@access(*ALL)
def dashboard(request):
    evs=events_for(request.user)
    alerts=[]
    for ev in evs.filter(status__in=s.ACTIVE):
        for text in s.conflicts(ev): alerts.append((ev,text))
    assets=Asset.objects.select_related('product','location') if role(request.user)!='Equipe operacional' else []
    stats={'physical':sum(a.available for a in assets),'out':0,'checking':0,'maintenance':sum(a.repairing for a in assets)}
    for line in EventLine.objects.filter(event__in=evs):
        stats['out']+=line.pending
        stats['checking']+=line.checking
    late=[e for e in evs.filter(expected_return__lt=timezone.now(),status__in=s.ACTIVE) if any(l.pending or l.checking for l in e.lines.all())]
    low=[]
    for p in Product.objects.filter(kind='supply',active=True):
        free=sum(a.available for a in p.asset_set.all())
        if free<p.minimum: low.append((p,free))
    return render(request,'inventory/dashboard.html',{'events':evs.filter(status__in=s.ACTIVE)[:8],'stats':stats,'alerts':alerts,'late':late,'low':low if role(request.user)!='Equipe operacional' else []})

@access(*ALL)
def events(request):
    qs=filtered_events(request)
    month=request.GET.get('month',timezone.localdate().strftime('%Y-%m'))
    try: first=datetime.strptime(month,'%Y-%m').date().replace(day=1)
    except ValueError: first=timezone.localdate().replace(day=1)
    weeks=[]
    for week in calendar.Calendar().monthdatescalendar(first.year,first.month):
        weeks.append([{'date':day,'current':day.month==first.month,'events':[e for e in qs if timezone.localtime(e.withdrawal).date()<=day<=timezone.localtime(e.release).date()]} for day in week])
    return render(request,'inventory/events.html',{'events':qs,'weeks':weeks,'month':first.strftime('%Y-%m'),'weekdays':['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'],'statuses':Event.STATUSES,'managers':get_user_model().objects.filter(is_active=True)})

@access('Gestor')
def event_edit(request,pk=None):
    ev=get_object_or_404(Event,pk=pk) if pk else None
    form=EventForm(request.POST or None,instance=ev)
    if request.method=='POST' and form.is_valid():
        try:
            ev=s.save_event(request.user,form)
            messages.success(request,'Evento salvo.')
            return redirect('event',pk=ev.pk)
        except ValidationError as exc: form.add_error(None,exc)
    return render(request,'inventory/form.html',{'form':form,'title':'Editar evento' if pk else 'Novo evento'})

@access(*ALL)
def event_detail(request,pk):
    ev=event_visible(request,pk)
    lines=list(ev.lines.select_related('asset__product__category','asset__location'))
    for line in lines: line.request_key=uuid.uuid4()
    return render(request,'inventory/event.html',{'event':ev,'lines':lines,'assets':Asset.objects.filter(active=True,product__active=True),'kits':Kit.objects.filter(active=True),'alerts':s.conflicts(ev) if ev.status in s.ACTIVE else [],'history':ev.audit_set.select_related('actor')[:80]})

@require_POST
@access('Gestor','Estoque')
def event_action(request,pk):
    ev=event_visible(request,pk)
    try:
        action=request.POST.get('action')
        if action=='add': s.add_line(request.user,pk,number(request,'asset'),number(request,'quantity'))
        elif action=='kit': s.add_kit(request.user,pk,number(request,'kit'))
        else: s.transition(request.user,pk,action)
        messages.success(request,'Operação registrada.')
    except (ValidationError,Asset.DoesNotExist,Kit.DoesNotExist) as exc: error(request,exc)
    return redirect('event',pk=ev.pk)

@require_POST
@access('Gestor','Estoque')
def line_action(request,pk):
    line=get_object_or_404(EventLine,pk=pk)
    event_visible(request,line.event_id)
    try:
        if request.POST.get('action')=='change': s.change_line(request.user,pk,number(request,'quantity'),number(request,'asset'),request.POST.get('reason',''))
        else:
            form=MovementForm(request.POST,request.FILES)
            if not form.is_valid(): raise ValidationError([str(e) for errors in form.errors.values() for e in errors])
            s.movement(request.user,pk,**form.cleaned_data)
        messages.success(request,'Movimentação registrada.')
    except (ValidationError,Asset.DoesNotExist) as exc: error(request,exc)
    return redirect('event',pk=line.event_id)

@require_POST
@access(*ALL)
def occurrence(request,pk):
    ev=event_visible(request,pk)
    reason=request.POST.get('reason','').strip()
    if reason: s.audit(request.user,'Ocorrência',ev,detail=reason[:3000]); messages.success(request,'Ocorrência registrada.')
    else: messages.error(request,'Descreva a ocorrência.')
    return redirect('event',pk=pk)

@access('Gestor','Estoque')
def catalog(request,kind):
    if kind not in CATALOG: raise Http404
    model,_,title=CATALOG[kind]
    qs=model.objects.all()
    q=request.GET.get('q','')
    if q:
        qs=qs.filter(Q(code__icontains=q)|Q(serial__icontains=q)|Q(product__name__icontains=q)) if model==Asset else qs.filter(name__icontains=q)
    return render(request,'inventory/catalog.html',{'objects':Paginator(qs,40).get_page(request.GET.get('page')),'kind':kind,'title':title})

@access('Gestor')
def catalog_edit(request,kind,pk=None):
    if kind not in CATALOG: raise Http404
    model,Form,title=CATALOG[kind]
    obj=get_object_or_404(model,pk=pk) if pk else None
    form=Form(request.POST or None,request.FILES or None,instance=obj)
    if request.method=='POST' and form.is_valid():
        try:
            obj=s.save_catalog(request.user,form)
            messages.success(request,'Cadastro salvo. Saldos são registrados em Ajustar saldo.')
            if kind=='equipamentos': return redirect('asset',token=obj.token)
            return redirect('catalog',kind=kind)
        except ValidationError as exc: form.add_error(None,exc)
    return render(request,'inventory/form.html',{'form':form,'title':title})

@access('Gestor')
def component(request,pk):
    kit=get_object_or_404(Kit,pk=pk)
    obj=get_object_or_404(KitComponent,pk=request.GET['component'],kit=kit) if request.GET.get('component') else KitComponent(kit=kit)
    form=ComponentForm(request.POST or None,instance=obj,initial={'kit':kit})
    form.fields['kit'].disabled=True
    if request.method=='POST' and form.is_valid():
        s.save_catalog(request.user,form)
        messages.success(request,'Componente salvo; eventos anteriores preservados.')
        return redirect('component',pk=pk)
    return render(request,'inventory/form.html',{'form':form,'title':f'Componentes · {kit}','components':kit.components.all()})

@access(*ALL)
def asset_detail(request,token):
    asset=get_object_or_404(Asset,token=token)
    lines=asset.lines.filter(event__in=events_for(request.user)).select_related('event')
    if role(request.user)=='Equipe operacional' and not lines.exists(): raise PermissionDenied
    return render(request,'inventory/asset.html',{'asset':asset,'lines':lines,'history':asset.audit_set.filter(Q(event__in=events_for(request.user))|Q(event__isnull=True))[:100] if role(request.user)!='Equipe operacional' else []})

@require_POST
@access('Gestor')
def adjust(request,token):
    asset=get_object_or_404(Asset,token=token)
    try:
        s.adjust(request.user,asset.pk,number(request,'delta'),request.POST.get('reason',''))
        messages.success(request,'Ajuste registrado.')
    except ValidationError as exc: error(request,exc)
    return redirect('asset',token=token)

@access(*ALL)
def qr(request,token):
    asset=get_object_or_404(Asset,token=token)
    if role(request.user)=='Equipe operacional' and not asset.lines.filter(event__in=events_for(request.user)).exists(): raise PermissionDenied
    stream=BytesIO()
    qrcode.make(f'{settings.PUBLIC_BASE_URL}/equipamento/{token}/').save(stream,format='PNG')
    return HttpResponse(stream.getvalue(),content_type='image/png')

@access('Gestor','Estoque')
def availability(request):
    form=RangeForm(request.GET or None)
    rows=[]
    if form.is_valid():
        for asset in Asset.objects.select_related('product','location').filter(active=True): rows.append((asset,s.capacity(asset,form.cleaned_data['start'],form.cleaned_data['end'])))
    return render(request,'inventory/availability.html',{'form':form,'rows':rows})

@access('Gestor','Estoque')
def maintenance(request):
    return render(request,'inventory/maintenance.html',{'orders':Maintenance.objects.select_related('asset__product')})

@access('Gestor','Estoque')
def maintenance_new(request):
    form=MaintenanceForm(request.POST or None,request.FILES or None)
    if request.method=='POST' and form.is_valid():
        try:
            s.open_maintenance(request.user,form)
            messages.success(request,'Manutenção aberta. Confira no painel as reservas afetadas.')
            return redirect('maintenance')
        except ValidationError as exc: form.add_error(None,exc)
    return render(request,'inventory/form.html',{'form':form,'title':'Abrir manutenção'})

@require_POST
@access('Gestor','Estoque')
def maintenance_close(request,pk):
    get_object_or_404(Maintenance,pk=pk)
    try:
        cost=Decimal(request.POST.get('cost','0').replace(',','.'))
        if not cost.is_finite(): raise InvalidOperation
        s.close_maintenance(request.user,pk,request.POST.get('condition',''),cost)
        messages.success(request,'Manutenção concluída e equipamento liberado.')
    except (ValidationError,InvalidOperation) as exc: error(request,exc if isinstance(exc,ValidationError) else ValidationError('Custo inválido.'))
    return redirect('maintenance')

@access('Gestor','Estoque')
def queue(request,mode):
    qs=events_for(request.user).filter(status__in=s.ACTIVE)
    return render(request,'inventory/queue.html',{'events':qs,'mode':mode,'title':'Separação e saídas' if mode=='saidas' else 'Devoluções e conferência'})

@access('Gestor','Estoque')
def reports(request):
    kind=request.GET.get('kind','patrimonio')
    evs=filtered_events(request)
    lines=EventLine.objects.filter(event__in=evs).select_related('asset__product','event__manager')
    if kind=='movimentacoes':
        headers=['Data','Autor','Ação','Evento','Equipamento','Quantidade','Detalhe']
        audits=Audit.objects.select_related('actor','event','asset')
        for key,lookup in [('from','at__date__gte'),('to','at__date__lte')]:
            if request.GET.get(key):
                try: audits=audits.filter(**{lookup:datetime.strptime(request.GET[key],'%Y-%m-%d').date()})
                except ValueError: pass
        rows=[[timezone.localtime(a.at).strftime('%d/%m/%Y %H:%M'),a.actor,a.action,a.event or '',a.asset or '',a.quantity,a.detail] for a in audits]
    elif kind=='manutencao':
        headers=['OS','Equipamento','Quantidade','Motivo','Prestador','Custo R$','Situação']
        orders=Maintenance.objects.select_related('asset__product')
        for key,lookup in [('from','opened_at__date__gte'),('to','opened_at__date__lte')]:
            if request.GET.get(key):
                try: orders=orders.filter(**{lookup:datetime.strptime(request.GET[key],'%Y-%m-%d').date()})
                except ValueError: pass
        rows=[[m.pk,m.asset,m.quantity,m.reason,m.provider,str(m.cost).replace('.',','),'Liberada' if m.closed_at else 'Aberta'] for m in orders]
    elif kind in ['eventos','pendencias']:
        headers=['Evento','Responsável','Equipamento','Planejado','Separado','Saiu','Retornou','A retornar','A conferir','Baixado','Dispensado']
        rows=[[l.event,l.event.manager,l.asset,l.quantity,l.separated,l.sent,l.returned,l.pending,l.checking,l.written_off,l.waived] for l in lines if kind=='eventos' or l.pending or l.checking or l.to_send]
    elif kind=='utilizacao':
        headers=['Equipamento','Eventos com saída','Unidades expedidas']
        rows=[]
        for a in Asset.objects.all():
            relevant=[l for l in lines if l.asset_id==a.pk and l.sent]
            rows.append([a,len(relevant),sum(l.sent for l in relevant)])
    else:
        kind='patrimonio'
        headers=['Código','Modelo','Tipo','Local','Total','Disponível físico','Em operação / conferência','Manutenção','Ativo','Valor de compra R$']
        rows=[[a.code,a.product,a.product.get_kind_display(),a.location,a.total,a.available,a.held,a.repairing,'Sim' if a.active else 'Não',str(a.value or '').replace('.',',')] for a in Asset.objects.select_related('product','location')]
    if request.GET.get('export')=='csv':
        response=HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition']=f'attachment; filename="{kind}.csv"'
        response.write('\ufeff')
        writer=csv.writer(response,delimiter=';')
        def safe(value):
            text=str(value)
            return "'"+text if text.lstrip().startswith(('=','+','-','@','\t','\r')) else text
        writer.writerow(headers)
        writer.writerows([[safe(c) for c in row] for row in rows])
        return response
    return render(request,'inventory/reports.html',{'headers':headers,'rows':rows,'kind':kind})

@access(*ALL)
def help_page(request):
    name=request.GET.get('doc','manual_usuario')
    if name not in ['manual_usuario','guia_operacional','etiquetas']: raise Http404
    text=(settings.BASE_DIR/'docs'/f'{name}.md').read_text()
    return render(request,'inventory/help.html',{'content':markdown.markdown(text,extensions=['tables','fenced_code']),'title':{'manual_usuario':'Manual de utilização','guia_operacional':'Organização da empresa','etiquetas':'Padrão de etiquetas'}[name]})

@access(*ALL)
def private_media(request,kind,pk):
    if kind=='asset':
        obj=get_object_or_404(Asset,pk=pk)
        if role(request.user)=='Equipe operacional' and not obj.lines.filter(event__in=events_for(request.user)).exists(): raise PermissionDenied
    elif kind=='audit':
        obj=get_object_or_404(Audit,pk=pk)
        if obj.event_id: event_visible(request,obj.event_id)
        elif role(request.user)=='Equipe operacional': raise PermissionDenied
    elif kind=='maintenance':
        if role(request.user)=='Equipe operacional': raise PermissionDenied
        obj=get_object_or_404(Maintenance,pk=pk)
    else: raise Http404
    if not obj.photo: raise Http404
    response=FileResponse(obj.photo.open('rb'))
    response['Cache-Control']='private, no-store'
    return response

@access('Gestor','Estoque')
def label_print(request):
    from .forms import LabelPrintForm
    form=LabelPrintForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        return render(request,'inventory/labels_print.html',{'assets':form.cleaned_data['assets'],'layout':form.cleaned_data['layout'],'company':settings.COMPANY_NAME})
    return render(request,'inventory/form.html',{'form':form,'title':'Gerar etiquetas','submit_label':'Gerar impressão','intro':'Selecione até 100 itens. Imprima em tamanho real (100%), sem cabeçalhos. Faça primeiro uma impressão de teste. Cada etiqueta mede 90 × 40 mm.'})

@access(*ALL)
def label_scan(request):
    from .forms import LabelPhotoForm
    from .labels import read_label
    from django.core.cache import cache
    form=LabelPhotoForm(request.POST or None,request.FILES or None)
    candidates=[]; method=''; warning=''
    ev=None
    if request.GET.get('event'):
        try: ev=event_visible(request,int(request.GET['event']))
        except ValueError: raise Http404
    if request.method=='POST' and form.is_valid():
        # Cache PostgreSQL: limite compartilhado entre workers. Nenhuma foto é persistida.
        key=f'label-scan:{request.user.pk}'
        if not cache.add(key,True,timeout=10):
            form.add_error(None,'Aguarde 10 segundos entre leituras de foto.')
        else:
            try:
                result=read_label(form.cleaned_data['photo']);method=result['method'];warning=result['warning']
                qs=Asset.objects.filter(Q(token__in=result['tokens'])|Q(code__in=result['codes'])).select_related('product','location')
                if role(request.user)=='Equipe operacional': qs=qs.filter(lines__event__in=events_for(request.user)).distinct()
                if ev: qs=qs.filter(lines__event=ev).distinct()
                candidates=list(qs)
                if not candidates and not warning: warning='Nenhum equipamento acessível foi identificado. Recorte a etiqueta, evite reflexos e tente novamente ou use o código manual.'
            except ValidationError as exc: form.add_error(None,exc)
    return render(request,'inventory/label_scan.html',{'form':form,'candidates':candidates,'method':method,'warning':warning,'event':ev})

from django.views.decorators.http import require_GET
@require_GET
def health(request):
    from django.db import connection, DatabaseError
    try:
        with connection.cursor() as cursor: cursor.execute('SELECT 1')
    except DatabaseError: return HttpResponse('unavailable',status=503,content_type='text/plain')
    return HttpResponse('ok',content_type='text/plain')
