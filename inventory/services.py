"""Todas as mutações operacionais são serializadas no PostgreSQL.
O bloqueio transacional global favorece correção e simplicidade para esta escala.
"""
from functools import wraps
from django.db import transaction, connection
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Asset, Event, EventLine, Kit, Maintenance, Audit
from .access import require
ACTIVE = ['reserved','picking','out','checking']

def serialized(fn):
    @wraps(fn)
    def wrapped(*args,**kwargs):
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_xact_lock(%s)', [73194021])
            return fn(*args,**kwargs)
    return wrapped

def audit(actor,action,event=None,asset=None,quantity=0,detail='',photo=''):
    return Audit.objects.create(actor=actor,action=action,event=event,asset=asset,quantity=quantity,detail=detail,photo=photo)

def positive(n):
    if n <= 0: raise ValidationError('Informe uma quantidade maior que zero.')

def capacity(asset,start,end,exclude=None):
    """Menor saldo em [start,end), varredura de intervalos, sem somar reservas disjuntas."""
    asset = Asset.objects.select_related('product').get(pk=asset.pk)
    if start >= end: raise ValidationError('O fim deve ser posterior ao início.')
    if not asset.active or not asset.product.active: return 0
    points = []
    now = timezone.now()
    for line in asset.lines.select_related('event').exclude(event_id=exclude):
        ev = line.event
        held = line.sent-line.cleared-line.written_off
        if held and ev.release <= now:
            points.extend([(start,held),(end,-held)])
        elif ev.status in ACTIVE:
            left,right = max(start,ev.withdrawal),min(end,ev.release)
            if left < right:
                points.extend([(left,line.quantity-line.waived-line.written_off),(right,-(line.quantity-line.waived-line.written_off))])
    used = peak = 0
    for moment,delta in sorted(points,key=lambda p:(p[0],p[1])):
        used += delta
        peak = max(peak,used)
    return max(0,asset.total-asset.repairing-peak)

def conflicts(event):
    result = []
    for line in event.lines.select_related('asset__product'):
        free = capacity(line.asset,event.withdrawal,event.release,event.pk)
        if line.quantity-line.waived-line.written_off > free:
            alternatives = [a.code for a in Asset.objects.filter(product=line.asset.product,active=True).exclude(pk=line.asset_id) if capacity(a,event.withdrawal,event.release,event.pk)>0]
            result.append(f'{line.asset.code}: solicitado {line.quantity}, disponível {free}. Alternativas: {", ".join(alternatives) or "nenhuma"}.')
    return result

def validate_reservation(event):
    errors = conflicts(event)
    if errors: raise ValidationError(errors)

@serialized
def save_event(actor,form):
    require(actor,['Gestor'])
    ev = form.instance
    old = Event.objects.get(pk=ev.pk) if ev.pk else None
    if old and old.status not in ['draft','reserved','picking']:
        raise ValidationError('Datas e cadastro só podem mudar antes da primeira saída.')
    if old: ev.status = old.status
    if old and old.status in ACTIVE: validate_reservation(ev)
    ev = form.save()
    audit(actor,'Evento atualizado' if old else 'Evento criado',ev,detail=str(form.cleaned_data))
    return ev

@serialized
def save_catalog(actor,form):
    require(actor,['Gestor'])
    obj = form.instance
    if isinstance(obj,Asset) and obj.pk:
        old = Asset.objects.get(pk=obj.pk)
        obj.total = old.total
        if old.product_id != obj.product_id and (old.total or old.lines.exists()):
            raise ValidationError('Não altere o modelo de um item com saldo ou histórico.')
    if obj.__class__.__name__ == 'Product' and obj.pk:
        old = obj.__class__.objects.get(pk=obj.pk)
        if old.kind != obj.kind and old.asset_set.exists():
            raise ValidationError('Não altere o tipo de controle após cadastrar equipamentos.')
    obj = form.save()
    audit(actor,'Cadastro atualizado',asset=obj if isinstance(obj,Asset) else None,detail=f'{obj.__class__.__name__} #{obj.pk}: {form.cleaned_data}')
    return obj

@serialized
def adjust(actor,asset_id,delta,reason):
    require(actor,['Gestor'])
    asset = Asset.objects.select_related('product').get(pk=asset_id)
    if not reason.strip() or not delta: raise ValidationError('Informe uma alteração não nula e justificativa.')
    total = asset.total+delta
    if total < asset.held+asset.repairing or total < 0: raise ValidationError('Ajuste deixaria saldo menor que as obrigações físicas.')
    if asset.product.kind == 'unit' and total not in [0,1]: raise ValidationError('Equipamentos individuais têm saldo 0 ou 1.')
    asset.total = total
    asset.save(update_fields=['total'])
    # Reduções não podem invalidar reservas confirmadas.
    for line in asset.lines.filter(event__status__in=ACTIVE): validate_reservation(line.event)
    audit(actor,'Ajuste de saldo',asset=asset,quantity=delta,detail=reason)

@serialized
def add_line(actor,event_id,asset_id,quantity,source='Avulso'):
    require(actor,['Gestor'])
    positive(quantity)
    ev = Event.objects.get(pk=event_id)
    if ev.status not in ['draft','reserved','picking']: raise ValidationError('Itens só podem mudar antes da saída.')
    asset = Asset.objects.select_related('product').get(pk=asset_id)
    line = EventLine.objects.filter(event=ev,asset=asset).first()
    new_quantity = quantity+(line.quantity if line else 0)
    if asset.product.kind == 'unit' and new_quantity != 1: raise ValidationError('Esta unidade já está no evento; selecione outra unidade.')
    if not asset.active or not asset.product.active: raise ValidationError('Equipamento inativo.')
    if line:
        line.quantity = new_quantity
        line.sources = [*line.sources,{'origem':source,'quantidade':quantity}]
        line.save()
    else: line = EventLine.objects.create(event=ev,asset=asset,quantity=quantity,sources=[{'origem':source,'quantidade':quantity}])
    if ev.status in ACTIVE: validate_reservation(ev)
    audit(actor,'Item adicionado',ev,asset,quantity,source)
    return line

@serialized
def add_kit(actor,event_id,kit_id):
    require(actor,['Gestor'])
    ev = Event.objects.get(pk=event_id)
    kit = Kit.objects.get(pk=kit_id,active=True)
    components = list(kit.components.select_related('product'))
    if not components: raise ValidationError('Kit sem componentes.')
    for component in components:
        remaining = component.quantity
        for asset in Asset.objects.filter(product=component.product,active=True).order_by('pk'):
            existing = ev.lines.filter(asset=asset).first()
            free = capacity(asset,ev.withdrawal,ev.release,ev.pk)-(existing.quantity if existing else 0)
            amount = min(remaining,max(0,free))
            if amount:
                add_line(actor,ev.pk,asset.pk,amount,f'Kit {kit.name} #{kit.pk}')
                remaining -= amount
            if not remaining: break
        if remaining: raise ValidationError(f'Kit incompleto: faltam {remaining} de {component.product}. Nenhum componente foi adicionado.')

@serialized
def change_line(actor,line_id,quantity,new_asset_id,reason):
    require(actor,['Gestor'])
    positive(quantity)
    line = EventLine.objects.select_related('event').get(pk=line_id)
    if not reason.strip(): raise ValidationError('Justifique o ajuste ou substituição.')
    if line.event.status not in ['draft','reserved','picking'] or line.sent: raise ValidationError('Ajuste permitido somente antes da saída.')
    old = f'{line.asset.code} × {line.quantity}'
    new_asset = Asset.objects.select_related('product').get(pk=new_asset_id)
    if new_asset.product.kind == 'unit' and quantity != 1: raise ValidationError('Unidade individual exige quantidade 1.')
    if not new_asset.active or not new_asset.product.active: raise ValidationError('Equipamento inativo.')
    if EventLine.objects.filter(event=line.event,asset=new_asset).exclude(pk=line.pk).exists(): raise ValidationError('O item substituto já está no evento. Ajuste a linha existente.')
    line.asset = new_asset
    line.quantity = quantity
    line.waived = 0
    line.separated = 0
    line.sources = [*line.sources,{'ajuste':reason,'anterior':old}]
    line.save()
    if line.event.status in ACTIVE: validate_reservation(line.event)
    audit(actor,'Item ajustado',line.event,new_asset,quantity,f'{old} → {new_asset.code} × {quantity}: {reason}')

@serialized
def transition(actor,event_id,action):
    require(actor,['Gestor'] if action in ['reserve','cancel','close'] else ['Gestor','Estoque'])
    ev = Event.objects.get(pk=event_id)
    if action == 'reserve':
        if ev.status != 'draft' or not ev.lines.exists(): raise ValidationError('Reserve um rascunho com itens.')
        if ev.release <= timezone.now(): raise ValidationError('Não confirme uma reserva já encerrada no calendário.')
        validate_reservation(ev)
        ev.status = 'reserved'
    elif action == 'picking':
        if ev.status != 'reserved': raise ValidationError('O evento precisa estar reservado.')
        ev.status = 'picking'
    elif action == 'cancel':
        if ev.status not in ['draft','reserved','picking'] or ev.lines.filter(sent__gt=0).exists(): raise ValidationError('Só é possível cancelar antes da saída.')
        ev.status = 'cancelled'
    elif action == 'close':
        if ev.status not in ['out','checking']: raise ValidationError('O evento ainda não está em operação.')
        if any(l.sent+l.waived != l.quantity or l.pending or l.checking for l in ev.lines.all()): raise ValidationError('Existem itens não expedidos, retornos ou conferências pendentes. Resolva-os antes de concluir.')
        ev.status = 'done'
    else: raise ValidationError('Ação inválida.')
    ev.save(update_fields=['status'])
    audit(actor,'Situação do evento',ev,detail=ev.get_status_display())

@serialized
def movement(actor,line_id,action,quantity,reason='',photo=''):
    require(actor,['Gestor'] if action in ['loss','waive'] else ['Gestor','Estoque'])
    positive(quantity)
    line = EventLine.objects.select_related('event','asset__product').get(pk=line_id)
    ev,asset = line.event,line.asset
    if ev.status not in ACTIVE: raise ValidationError('Evento não está ativo.')
    if action == 'separate':
        if quantity > line.quantity-line.separated-line.waived: raise ValidationError('Quantidade supera a separação pendente.')
        line.separated += quantity
        if ev.status == 'reserved': ev.status = 'picking'
    elif action == 'dispatch':
        validate_reservation(ev)
        if quantity > min(line.separated-line.sent,line.to_send) or quantity > asset.available: raise ValidationError('Quantidade supera os itens separados ou fisicamente disponíveis.')
        line.sent += quantity
        ev.status = 'out'
    elif action == 'return':
        if quantity > line.pending: raise ValidationError('Quantidade supera o retorno pendente.')
        if not reason.strip(): raise ValidationError('Informe a condição dos itens devolvidos.')
        line.returned += quantity
        ev.status = 'checking'
    elif action in ['clear','damage']:
        if quantity > line.checking: raise ValidationError('Quantidade supera os itens aguardando conferência.')
        if not reason.strip(): raise ValidationError('Informe a condição constatada na conferência.')
        line.cleared += quantity
        asset.condition = reason
        asset.save(update_fields=['condition'])
        if action == 'damage':
            order = Maintenance.objects.create(asset=asset,quantity=quantity,kind='corrective',reason=reason,provider=actor.get_username(),photo=photo)
            photo = order.photo.name if order.photo else ''
    elif action == 'waive':
        if not reason.strip() or quantity > line.to_send: raise ValidationError('Justifique e informe apenas a quantidade ainda não expedida.')
        line.waived += quantity
        line.separated = min(line.separated,line.quantity-line.waived)
    elif action in ['loss','consume']:
        if action == 'consume' and asset.product.kind != 'supply': raise ValidationError('Consumo é exclusivo para consumíveis.')
        if not reason.strip() or quantity > line.pending: raise ValidationError('Informe justificativa e quantidade ainda não devolvida.')
        line.written_off += quantity
        asset.total -= quantity
        asset.save(update_fields=['total'])
    else: raise ValidationError('Movimentação inválida.')
    line.save()
    ev.save(update_fields=['status'])
    labels = {'separate':'Separação','dispatch':'Saída','return':'Devolução','clear':'Conferência e liberação','damage':'Avaria e manutenção','loss':'Baixa por perda','consume':'Consumo','waive':'Dispensa de expedição autorizada'}
    audit(actor,labels[action],ev,asset,quantity,reason,photo)

@serialized
def open_maintenance(actor,form):
    require(actor,['Gestor','Estoque'])
    obj = form.instance
    obj.asset.refresh_from_db()
    positive(obj.quantity)
    if obj.quantity > obj.asset.available: raise ValidationError('Quantidade maior que o saldo físico disponível. Para avarias retornadas, use a conferência do evento.')
    obj = form.save()
    audit(actor,'Manutenção aberta',asset=obj.asset,quantity=obj.quantity,detail=f'OS {obj.pk}: {obj.reason}')
    return obj

@serialized
def close_maintenance(actor,pk,condition,cost):
    require(actor,['Gestor','Estoque'])
    obj = Maintenance.objects.get(pk=pk)
    if obj.closed_at: raise ValidationError('Ordem já concluída.')
    if not condition.strip() or cost < 0: raise ValidationError('Informe condição final e custo não negativo.')
    obj.final_condition,obj.cost,obj.closed_at = condition,cost,timezone.now()
    obj.full_clean()
    obj.save()
    obj.asset.condition = condition
    obj.asset.save(update_fields=['condition'])
    audit(actor,'Manutenção liberada',asset=obj.asset,quantity=obj.quantity,detail=f'OS {obj.pk}: {condition}. Custo R$ {cost}')
