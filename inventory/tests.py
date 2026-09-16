from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import connection, connections
from django.test import TestCase, TransactionTestCase, Client as WebClient
from django.utils import timezone
from .models import *
from .forms import EventForm, MaintenanceForm
from . import services as s

class Fixtures:
    def setup_data(self):
        self.user=get_user_model().objects.create_superuser(username='admin',password='Temporary-test-only-928!')
        self.category=Category.objects.create(name='Som')
        self.location=Location.objects.create(name='A1')
        self.product=Product.objects.create(name='Caixa',category=self.category,kind='unit')
        self.bulk_product=Product.objects.create(name='Cabos',category=self.category,kind='bulk')
        self.asset=Asset.objects.create(code='CX1',product=self.product,location=self.location)
        self.bulk=Asset.objects.create(code='CABO',product=self.bulk_product,location=self.location)
        s.adjust(self.user,self.asset.pk,1,'Inventário inicial')
        s.adjust(self.user,self.bulk.pk,10,'Inventário inicial')
        self.customer=Client.objects.create(name='Cliente')
        self.t=timezone.now()+timedelta(days=1)
    def event(self,name='Evento',start=None,hours=12):
        t=start or self.t
        return Event.objects.create(name=name,client=self.customer,place='Praça',manager=self.user,withdrawal=t,assembly=t+timedelta(hours=1),start=t+timedelta(hours=2),end=t+timedelta(hours=3),expected_return=t+timedelta(hours=hours-1),release=t+timedelta(hours=hours))
    def reserve(self,asset=None,qty=1,start=None):
        ev=self.event(start=start)
        line=s.add_line(self.user,ev.pk,(asset or self.asset).pk,qty)
        s.transition(self.user,ev.pk,'reserve')
        return ev,line
    def send(self,line,qty):
        s.movement(self.user,line.pk,'separate',qty)
        s.movement(self.user,line.pk,'dispatch',qty)

class OperationsTests(Fixtures,TestCase):
    def setUp(self): self.setup_data()
    def test_conflicting_unit_reservations(self):
        self.reserve()
        ev=self.event('Conflito')
        s.add_line(self.user,ev.pk,self.asset.pk,1)
        with self.assertRaises(ValidationError): s.transition(self.user,ev.pk,'reserve')
        ev.refresh_from_db();self.assertEqual(ev.status,'draft')
    def test_draft_and_cancel_do_not_block(self):
        ev=self.event();s.add_line(self.user,ev.pk,self.asset.pk,1)
        self.assertEqual(s.capacity(self.asset,ev.withdrawal,ev.release),1)
        s.transition(self.user,ev.pk,'reserve');s.transition(self.user,ev.pk,'cancel')
        self.assertEqual(s.capacity(self.asset,ev.withdrawal,ev.release),1)
    def test_three_simultaneous_events_quantity(self):
        for i in range(3): self.reserve(self.bulk,3)
        self.assertEqual(s.capacity(self.bulk,self.t,self.t+timedelta(hours=12)),1)
        with self.assertRaises(ValidationError): self.reserve(self.bulk,2)
    def test_disjoint_reservations_not_added_together(self):
        self.reserve(self.bulk,6)
        self.reserve(self.bulk,6,start=self.t+timedelta(hours=12))
        self.assertEqual(s.capacity(self.bulk,self.t,self.t+timedelta(hours=24)),4)
    def test_touching_intervals_allowed(self):
        self.reserve();self.reserve(start=self.t+timedelta(hours=12))
    def test_partial_return_and_inspection(self):
        ev,line=self.reserve(self.bulk,6)
        self.send(line,4)
        s.movement(self.user,line.pk,'return',2,'Bom')
        self.bulk.refresh_from_db();self.assertEqual(self.bulk.available,6)
        s.movement(self.user,line.pk,'clear',1,'Testado')
        self.bulk.refresh_from_db();self.assertEqual(self.bulk.available,7)
        line.refresh_from_db();self.assertEqual((line.pending,line.checking,line.to_send),(2,1,2))
        with self.assertRaises(ValidationError): s.transition(self.user,ev.pk,'close')
    def test_dispatch_requires_separation_and_physical_balance(self):
        ev,line=self.reserve()
        with self.assertRaises(ValidationError): s.movement(self.user,line.pk,'dispatch',1)
        self.send(line,1)
        with self.assertRaises(ValidationError): s.movement(self.user,line.pk,'dispatch',1)
        with self.assertRaises(ValidationError): s.movement(self.user,line.pk,'return',2,'Bom')
    def test_full_flow_to_close(self):
        ev,line=self.reserve();self.send(line,1)
        s.movement(self.user,line.pk,'return',1,'Bom')
        s.movement(self.user,line.pk,'clear',1,'Teste aprovado')
        s.transition(self.user,ev.pk,'close')
        ev.refresh_from_db();self.assertEqual(ev.status,'done')
        self.asset.refresh_from_db();self.assertEqual(self.asset.available,1)
    def test_damage_blocks_until_explicit_release(self):
        ev,line=self.reserve();self.send(line,1)
        s.movement(self.user,line.pk,'return',1,'Falha')
        s.movement(self.user,line.pk,'damage',1,'Não liga')
        self.asset.refresh_from_db();self.assertEqual(self.asset.available,0)
        self.assertEqual(s.capacity(self.asset,self.t+timedelta(days=2),self.t+timedelta(days=3)),0)
        order=Maintenance.objects.get()
        with self.assertRaises(ValidationError): s.close_maintenance(self.user,order.pk,'',Decimal('10'))
        s.close_maintenance(self.user,order.pk,'Reparado e testado',Decimal('150'))
        self.asset.refresh_from_db();self.assertEqual(self.asset.available,1)
    def test_maintenance_warns_existing_reservation(self):
        ev,line=self.reserve()
        form=MaintenanceForm(data={'asset':self.asset.pk,'quantity':1,'kind':'preventive','reason':'Revisão','provider':'Técnico','cost':'0'})
        self.assertTrue(form.is_valid(),form.errors)
        s.open_maintenance(self.user,form)
        self.assertTrue(s.conflicts(ev))
        s.movement(self.user,line.pk,'separate',1)
        with self.assertRaises(ValidationError): s.movement(self.user,line.pk,'dispatch',1)
    def test_late_return_affects_future(self):
        ev,line=self.reserve();self.send(line,1)
        Event.objects.filter(pk=ev.pk).update(withdrawal=self.t-timedelta(days=4),assembly=self.t-timedelta(days=4)+timedelta(hours=1),start=self.t-timedelta(days=4)+timedelta(hours=2),end=self.t-timedelta(days=4)+timedelta(hours=3),expected_return=self.t-timedelta(days=3,hours=1),release=self.t-timedelta(days=3))
        self.asset.refresh_from_db()
        self.assertEqual(s.capacity(self.asset,self.t,self.t+timedelta(hours=12)),0)
        s.movement(self.user,line.pk,'return',1,'Bom')
        self.assertEqual(s.capacity(self.asset,self.t,self.t+timedelta(hours=12)),0)
        s.movement(self.user,line.pk,'clear',1,'Bom')
        self.assertEqual(s.capacity(self.asset,self.t,self.t+timedelta(hours=12)),1)
    def test_kit_snapshot_and_shared_components(self):
        kit=Kit.objects.create(name='Cabos')
        c=KitComponent.objects.create(kit=kit,product=self.bulk_product,quantity=3)
        ev=self.event();s.add_kit(self.user,ev.pk,kit.pk);s.add_kit(self.user,ev.pk,kit.pk)
        s.add_line(self.user,ev.pk,self.bulk.pk,1)
        self.assertEqual(ev.lines.count(),1);self.assertEqual(ev.lines.get().quantity,7)
        c.quantity=8;c.save()
        self.assertEqual(ev.lines.get().quantity,7)
        with self.assertRaises(ValidationError): s.add_kit(self.user,ev.pk,kit.pk)
        self.assertEqual(ev.lines.get().quantity,7)
    def test_substitution_checks_conflict(self):
        ev,line=self.reserve()
        a=Asset.objects.create(code='CX2',product=self.product,location=self.location)
        s.adjust(self.user,a.pk,1,'Inventário')
        s.change_line(self.user,line.pk,1,a.pk,'Substituição autorizada')
        line.refresh_from_db();self.assertEqual(line.asset_id,a.pk)
        self.reserve()
        with self.assertRaises(ValidationError): s.change_line(self.user,line.pk,1,self.asset.pk,'Voltar')
    def test_date_change_revalidates(self):
        self.reserve()
        ev,line=self.reserve(start=self.t+timedelta(days=2))
        data={f:getattr(ev,f) for f in ['name','client','place','contact','manager','withdrawal','assembly','start','end','expected_return','release','notes']}
        data['client']=self.customer.pk;data['manager']=self.user.pk
        for key in ['withdrawal','assembly','start','end','expected_return','release']:data[key]=(data[key]-timedelta(days=2)).strftime('%Y-%m-%dT%H:%M')
        form=EventForm(data=data,instance=ev)
        self.assertTrue(form.is_valid(),form.errors)
        with self.assertRaises(ValidationError):s.save_event(self.user,form)
    def test_adjustment_preserves_history_and_reservations(self):
        before=Audit.objects.count()
        s.adjust(self.user,self.bulk.pk,-2,'Contagem física')
        self.bulk.refresh_from_db();self.assertEqual(self.bulk.total,8)
        self.assertEqual(Audit.objects.count(),before+1)
        ev,line=self.reserve(self.bulk,8)
        with self.assertRaises(ValidationError):s.adjust(self.user,self.bulk.pk,-1,'Erro')
        self.bulk.refresh_from_db();self.assertEqual(self.bulk.total,8)
    def test_consume_return_and_loss(self):
        p=Product.objects.create(name='Fita',category=self.category,kind='supply')
        a=Asset.objects.create(code='FITA',product=p,location=self.location)
        s.adjust(self.user,a.pk,10,'Inicial')
        ev,line=self.reserve(a,5);self.send(line,5)
        s.movement(self.user,line.pk,'consume',3,'Usado no evento')
        s.movement(self.user,line.pk,'return',2,'Lacrado');s.movement(self.user,line.pk,'clear',2,'Bom')
        s.transition(self.user,ev.pk,'close')
        a.refresh_from_db();self.assertEqual((a.total,a.available),(7,7))
        ev,line=self.reserve();self.send(line,1);s.movement(self.user,line.pk,'loss',1,'Perda aprovada')
        self.asset.refresh_from_db();self.assertEqual(self.asset.total,0)
        self.assertEqual(line.event.audit_set.filter(action='Baixa por perda').count(),1)
    def test_consumed_material_is_not_reserved_twice(self):
        p=Product.objects.create(name='Consumível',category=self.category,kind='supply')
        a=Asset.objects.create(code='CONS',product=p,location=self.location)
        s.adjust(self.user,a.pk,6,'Inicial')
        reservations=[self.reserve(a,2) for _ in range(3)]
        for ev,line in reservations:
            self.send(line,2)
            s.movement(self.user,line.pk,'consume',2,'Consumo real')
        a.refresh_from_db()
        self.assertEqual(a.total,0)
        self.assertEqual(a.available,0)

    def test_damage_photo_is_shared_without_moving_upload_twice(self):
        import tempfile
        from django.core.files.uploadedfile import TemporaryUploadedFile
        from PIL import Image
        ev,line=self.reserve();self.send(line,1)
        s.movement(self.user,line.pk,'return',1,'Avariado')
        with tempfile.TemporaryDirectory() as media, self.settings(MEDIA_ROOT=media):
            upload=TemporaryUploadedFile('avaria.png','image/png',100,None)
            Image.new('RGB',(10,10)).save(upload.file,format='PNG')
            upload.file.seek(0)
            s.movement(self.user,line.pk,'damage',1,'Defeito identificado',upload)
            order=Maintenance.objects.get()
            audit=Audit.objects.get(action='Avaria e manutenção')
            self.assertEqual(order.photo.name,audit.photo.name)
            self.assertTrue(order.photo.storage.exists(order.photo.name))

    def test_authorized_waiver_resolves_unshipped(self):
        ev,line=self.reserve(self.bulk,5);self.send(line,2)
        s.movement(self.user,line.pk,'waive',3,'Cliente dispensou três cabos')
        s.movement(self.user,line.pk,'return',2,'Bom');s.movement(self.user,line.pk,'clear',2,'Bom')
        s.transition(self.user,ev.pk,'close')
        line.refresh_from_db();self.assertEqual(line.quantity,5);self.assertEqual(line.waived,3)
    def test_server_permissions_and_assigned_events(self):
        operator=get_user_model().objects.create_user('equipe')
        operator.groups.add(Group.objects.create(name='Equipe operacional'))
        ev,line=self.reserve()
        web=WebClient();web.force_login(operator)
        self.assertEqual(web.get(f'/eventos/{ev.pk}/').status_code,404)
        self.assertEqual(web.get('/relatorios/').status_code,403)
        self.assertEqual(web.post(f'/itens/{line.pk}/acao/',{'action':'dispatch','quantity':1}).status_code,403)
        ev.team.add(operator)
        self.assertEqual(web.get(f'/eventos/{ev.pk}/').status_code,200)
        self.assertEqual(web.post(f'/eventos/{ev.pk}/ocorrencia/',{'reason':'Chegamos ao local'}).status_code,302)
        with self.assertRaises(PermissionDenied):s.adjust(operator,self.asset.pk,1,'Teste')
    def test_warehouse_cannot_write_off_or_reserve(self):
        user=get_user_model().objects.create_user('estoque');user.groups.add(Group.objects.create(name='Estoque'))
        ev,line=self.reserve()
        with self.assertRaises(PermissionDenied):s.movement(user,line.pk,'loss',1,'Perda')
        with self.assertRaises(PermissionDenied):s.transition(user,ev.pk,'cancel')
    def test_csrf_and_private_qr(self):
        web=WebClient(enforce_csrf_checks=True);web.force_login(self.user)
        ev,line=self.reserve()
        self.assertEqual(web.post(f'/eventos/{ev.pk}/acao/',{'action':'cancel'}).status_code,403)
        self.assertEqual(WebClient().get(f'/equipamento/{self.asset.token}/qr/').status_code,302)
    def test_pages_render(self):
        self.client.force_login(self.user)
        ev,line=self.reserve()
        for url in ['/', '/eventos/','/eventos/novo/',f'/eventos/{ev.pk}/',f'/eventos/{ev.pk}/editar/','/cadastros/equipamentos/','/cadastros/equipamentos/novo/','/cadastros/modelos/','/cadastros/kits/',f'/equipamento/{self.asset.token}/',f'/equipamento/{self.asset.token}/qr/','/disponibilidade/','/manutencao/','/manutencao/nova/','/operacao/saidas/','/operacao/devolucoes/','/relatorios/','/relatorios/?kind=movimentacoes','/relatorios/?kind=eventos','/relatorios/?kind=pendencias','/relatorios/?kind=manutencao','/relatorios/?kind=utilizacao','/relatorios/?export=csv','/ajuda/','/ajuda/?doc=guia_operacional']:
            with self.subTest(url=url):self.assertEqual(self.client.get(url).status_code,200)
    def test_csv_formula_injection(self):
        self.asset.code='=1+1';self.asset.save()
        self.client.force_login(self.user)
        response=self.client.get('/relatorios/?export=csv')
        self.assertIn("'=1+1",response.content.decode())
    def test_invalid_quantity_does_not_crash(self):
        ev,line=self.reserve();self.client.force_login(self.user)
        response=self.client.post(f'/eventos/{ev.pk}/acao/',{'action':'add','asset':'abc','quantity':'bad'})
        self.assertEqual(response.status_code,302)

class ConcurrencyTests(Fixtures,TransactionTestCase):
    def setUp(self): self.setup_data()
    def test_two_simultaneous_reservations_only_one_commits(self):
        events=[self.event('A'),self.event('B')]
        for ev in events:s.add_line(self.user,ev.pk,self.asset.pk,1)
        barrier=Barrier(2)
        def worker(pk):
            try:
                user=get_user_model().objects.get(pk=self.user.pk)
                barrier.wait(timeout=10)
                try:s.transition(user,pk,'reserve');return 'ok'
                except ValidationError:return 'conflict'
            finally:connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(worker,[ev.pk for ev in events]))
        self.assertCountEqual(results,['ok','conflict'])
        self.assertEqual(Event.objects.filter(status='reserved').count(),1)
