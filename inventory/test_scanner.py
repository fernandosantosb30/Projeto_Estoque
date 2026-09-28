import uuid
from django.test import TestCase
from django.conf import settings
from django.contrib.auth.models import Group
from .tests import Fixtures
from .models import Asset, Audit
from .forms import AssetBatchForm
from . import services

class ScannerTests(Fixtures,TestCase):
    def setUp(self):
        self.setup_data(); self.client.force_login(self.user)
    def test_scanner_code_and_qr_are_read_only(self):
        before=Audit.objects.count()
        for code in [self.asset.code, f'{settings.PUBLIC_BASE_URL}/equipamento/{self.asset.token}/']:
            response=self.client.get('/scanner/',{'code':code})
            self.assertRedirects(response,f'/equipamento/{self.asset.token}/')
        self.assertEqual(Audit.objects.count(),before)
    def test_scanner_unknown_and_foreign_url(self):
        for code in ['EQ-999999',f'https://foreign.invalid/equipamento/{self.asset.token}/']:
            self.assertContains(self.client.get('/scanner/',{'code':code}),'Etiqueta não encontrada')
    def test_operator_cannot_read_unassigned_equipment(self):
        self.user.is_superuser=False; self.user.save()
        self.user.groups.add(Group.objects.get_or_create(name='Equipe operacional')[0])
        self.assertContains(self.client.get('/scanner/',{'code':self.asset.code}),'Etiqueta não encontrada')
        self.assertEqual(self.client.get('/equipamentos/lote/').status_code,403)
    def test_batch_assigns_unique_labels_stock_and_no_replay(self):
        payload={'request_key':str(uuid.uuid4()),'product':self.product.pk,'location':self.location.pk,'quantity':3,'condition':'Bom','confirm':True}
        before=Asset.objects.count()
        response=self.client.post('/equipamentos/lote/',payload)
        self.assertEqual(response.status_code,302)
        self.assertEqual(Asset.objects.count(),before+3)
        assets=Asset.objects.filter(code__startswith='EQ-')
        self.assertEqual(list(assets.order_by('code').values_list('code',flat=True)),['EQ-000001','EQ-000002','EQ-000003'])
        self.assertTrue(all(a.total==1 for a in assets))
        self.assertContains(self.client.get(response.url),'checked')
        self.client.post('/equipamentos/lote/',payload)
        self.assertEqual(Asset.objects.count(),before+3)
    def test_batch_rejects_bulk_and_unconfirmed(self):
        payload={'request_key':uuid.uuid4(),'product':self.bulk_product.pk,'location':self.location.pk,'quantity':3,'condition':'Bom','confirm':True}
        self.assertFalse(AssetBatchForm(payload).is_valid())
        payload.update(product=self.product.pk,confirm=False)
        self.assertFalse(AssetBatchForm(payload).is_valid())
