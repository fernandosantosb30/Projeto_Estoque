from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
class Command(BaseCommand):
    help='Cria os quatro perfis operacionais, sem criar usuários ou senhas.'
    def handle(self,*args,**kwargs):
        for name in ['Administrador','Gestor','Estoque','Equipe operacional']: Group.objects.get_or_create(name=name)
        self.stdout.write(self.style.SUCCESS('Perfis configurados. Atribua um perfil a cada usuário pelo admin.'))
