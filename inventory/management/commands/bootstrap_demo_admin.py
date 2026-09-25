"""Cria o primeiro administrador da demonstração sem shell remoto."""
import os
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection


class Command(BaseCommand):
    help = 'Cria uma única conta inicial via ambiente, exclusivamente em DEMO_MODE.'

    def handle(self, *args, **options):
        username = os.environ.get('BOOTSTRAP_ADMIN_USERNAME', '').strip()
        password = os.environ.get('BOOTSTRAP_ADMIN_PASSWORD', '')
        if not username and not password:
            return
        if not settings.DEMO_MODE:
            raise CommandError('Remova BOOTSTRAP_ADMIN_* fora do modo de demonstração.')
        if not username or not password:
            raise CommandError('Informe ambas as variáveis BOOTSTRAP_ADMIN_USERNAME e BOOTSTRAP_ADMIN_PASSWORD.')
        User = get_user_model()
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute('SELECT pg_advisory_xact_lock(%s)', [73194022])
            existing = User.objects.filter(username=username).first()
            if existing:
                if not existing.is_superuser or not existing.is_active:
                    raise CommandError('A conta inicial já existe sem acesso administrativo ativo. Escolha outro nome.')
                self.stdout.write('Administrador já existe; senha e permissões preservadas.')
                return
            if User.objects.filter(is_superuser=True).exists():
                raise CommandError('Já existe administrador. Remova BOOTSTRAP_ADMIN_* e use a conta existente.')
            user = User(username=username, is_staff=True, is_superuser=True)
            try:
                user.full_clean(exclude=['password'])
                validate_password(password, user=user)
            except ValidationError:
                raise CommandError('Nome de usuário inválido ou senha fraca. Use nome válido e senha longa, exclusiva e não comum.') from None
            user.set_password(password)
            user.save()
        self.stdout.write(self.style.SUCCESS('Administrador criado. Remova BOOTSTRAP_ADMIN_* do Render após confirmar o login.'))
