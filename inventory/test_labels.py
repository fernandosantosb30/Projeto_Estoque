from io import BytesIO
from unittest.mock import patch
import uuid
import qrcode
from PIL import Image, ImageDraw, ImageFont
from django.test import TestCase, SimpleTestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .tests import Fixtures
from .models import Asset, Audit, CodeSequence
from .forms import AssetForm
from .labels import read_label, qr_token, CODE_PATTERN
from . import services as s

def upload(image):
    b=BytesIO();image.save(b,format='PNG')
    return SimpleUploadedFile('etiqueta.png',b.getvalue(),content_type='image/png')

class LabelImageTests(SimpleTestCase):
    def test_real_qr_from_photo(self):
        from django.conf import settings
        token=uuid.uuid4()
        qr=qrcode.make(f'{settings.PUBLIC_BASE_URL}/equipamento/{token}/').convert('RGB')
        canvas=Image.new('RGB',(900,500),'white');canvas.paste(qr,(50,30))
        result=read_label(upload(canvas))
        self.assertEqual(result['tokens'],{token})
        self.assertEqual(result['method'],'QR Code')
    def test_real_ocr_standard_code(self):
        image=Image.new('RGB',(1000,350),'white')
        draw=ImageDraw.Draw(image)
        font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf',76)
        draw.text((60,100),'EQ-000123',font=font,fill='black')
        result=read_label(upload(image))
        self.assertEqual(result['codes'],{'EQ-000123'},result)
    def test_qr_does_not_follow_external_url(self):
        self.assertIsNone(qr_token(f'https://evil.invalid/equipamento/{uuid.uuid4()}/'))
        self.assertIsNone(qr_token('file:///etc/passwd'))
    def test_no_fuzzy_digits(self):
        self.assertEqual(CODE_PATTERN.findall('EQ-OOO123 EQ-0001234 XXEQ-000123'),[])
    def test_invalid_photo(self):
        with self.assertRaises(ValidationError):read_label(SimpleUploadedFile('fake.png',b'not-an-image'))
    def test_missing_ocr_returns_manual_fallback(self):
        import pytesseract
        with patch('pytesseract.image_to_string',side_effect=pytesseract.TesseractNotFoundError()):
            result=read_label(upload(Image.new('RGB',(100,100),'white')))
        self.assertIn('indisponível',result['warning'])

class LabelWorkflowTests(Fixtures,TestCase):
    def setUp(self):
        self.setup_data();cache.clear();self.client.force_login(self.user)
    def form(self,instance=None):
        return AssetForm(data={'product':self.product.pk,'location':self.location.pk,'condition':'Bom','active':True,'code':'CLIENTE-TENTOU'},instance=instance)
    def test_generated_codes_and_immutable_code(self):
        form=self.form();self.assertTrue(form.is_valid(),form.errors)
        asset=s.save_catalog(self.user,form);self.assertEqual(asset.code,'EQ-000001')
        edit=self.form(asset);self.assertTrue(edit.is_valid(),edit.errors)
        s.save_catalog(self.user,edit);asset.refresh_from_db();self.assertEqual(asset.code,'EQ-000001')
        form=self.form();self.assertTrue(form.is_valid());second=s.save_catalog(self.user,form)
        self.assertEqual(second.code,'EQ-000002')
    def test_legacy_codes_preserved_and_sequence_skips_collision(self):
        Asset.objects.create(code='EQ-000001',product=self.product,location=self.location)
        form=self.form();self.assertTrue(form.is_valid());asset=s.save_catalog(self.user,form)
        self.assertEqual(asset.code,'EQ-000002')
        form=self.form(self.asset);self.assertTrue(form.is_valid());s.save_catalog(self.user,form)
        self.asset.refresh_from_db();self.assertEqual(self.asset.code,'CX1')
    def test_print_and_scan_pages(self):
        self.assertEqual(self.client.get('/etiquetas/').status_code,200)
        response=self.client.post('/etiquetas/',{'assets':[self.asset.pk],'layout':'a4'})
        self.assertContains(response,'CX1');self.assertContains(response,'90mm')
        self.assertEqual(self.client.get('/identificar/').status_code,200)
    def test_photo_recognition_does_not_change_stock(self):
        from django.conf import settings
        before=Audit.objects.count()
        response=self.client.post('/identificar/',{'photo':upload(qrcode.make(f'{settings.PUBLIC_BASE_URL}/equipamento/{self.asset.token}/').convert('RGB'))})
        self.assertContains(response,'Conferi, abrir ficha')
        self.assertEqual(Audit.objects.count(),before)
        self.asset.refresh_from_db();self.assertEqual(self.asset.total,1)
    def test_scan_is_rate_limited(self):
        cache.set(f'label-scan:{self.user.pk}',True,10)
        response=self.client.post('/identificar/',{'photo':upload(Image.new('RGB',(100,100),'white'))})
        self.assertContains(response,'Aguarde 10 segundos')
    def test_resubmission_of_movement_is_not_duplicated(self):
        ev,line=self.reserve(self.bulk,5)
        key=uuid.uuid4()
        s.movement(self.user,line.pk,'separate',2,request_key=key)
        s.movement(self.user,line.pk,'separate',2,request_key=key)
        line.refresh_from_db();self.assertEqual(line.separated,2)
        self.assertEqual(Audit.objects.filter(request_key=key).count(),1)
    def test_login_lockout(self):
        self.client.logout()
        for _ in range(5):self.client.post('/entrar/',{'username':'admin','password':'wrong'})
        response=self.client.post('/entrar/',{'username':'admin','password':'Temporary-test-only-928!'})
        self.assertEqual(response.status_code,429)
    def test_health_check(self):
        self.client.logout()
        self.assertEqual(self.client.get('/healthz/').status_code,200)
    def test_damage_on_returned_item_does_not_block_other_dispatch(self):
        ev,line=self.reserve();self.send(line,1)
        s.movement(self.user,line.pk,'return',1,'Falha');s.movement(self.user,line.pk,'damage',1,'Falha')
        # Existing bulk line in event: simulated planning before first departure.
        from .models import EventLine
        cable=EventLine.objects.create(event=ev,asset=self.bulk,quantity=2)
        s.movement(self.user,cable.pk,'separate',2)
        s.movement(self.user,cable.pk,'dispatch',2)
        cable.refresh_from_db();self.assertEqual(cable.sent,2)
