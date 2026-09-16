import secrets
from pathlib import Path
from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command
from django.contrib.auth import get_user_model
from inventory.models import Event
class Command(BaseCommand):
    help='Prepara conta exclusiva e dados fictícios para avaliação local; grava acesso em arquivo privado.'
    def handle(self,*args,**kwargs):
        if not settings.DEBUG or Event.objects.exists():raise CommandError('Somente desenvolvimento e banco sem eventos.')
        if get_user_model().objects.filter(username='demonstracao').exists():raise CommandError('Conta demo já existe; não será alterada.')
        password=secrets.token_urlsafe(16)
        get_user_model().objects.create_superuser('demonstracao',password=password)
        path=settings.BASE_DIR/'.demo-access.txt'
        path.touch(mode=0o600,exist_ok=False)
        path.write_text('Acesso local de demonstração\nEndereço: http://127.0.0.1:8000\nUsuário: demonstracao\nSenha: '+password+'\n\nNão use esta conta em produção. Dados inteiramente fictícios.\n')
        call_command('seed_demo',username='demonstracao')
        self.stdout.write('Acesso salvo em .demo-access.txt (privado; não versionar).')
