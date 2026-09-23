import shutil
import tempfile
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
class Command(BaseCommand):
    help='Verifica banco, OCR e escrita no armazenamento antes de iniciar o serviço.'
    def handle(self,*args,**kwargs):
        if not shutil.which(settings.TESSERACT_CMD or 'tesseract'):
            raise CommandError('Tesseract não encontrado. Use o Dockerfile incluído.')
        root=Path(settings.MEDIA_ROOT)
        root.mkdir(parents=True,exist_ok=True)
        try:
            with tempfile.TemporaryFile(dir=root) as f:f.write(b'ready');f.flush()
        except OSError as exc:raise CommandError('MEDIA_ROOT não permite escrita.') from exc
        with connection.cursor() as cursor:cursor.execute('SELECT 1')
        self.stdout.write(self.style.SUCCESS('Banco, OCR e armazenamento disponíveis.'))
