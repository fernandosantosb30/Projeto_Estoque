from io import StringIO
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings


@override_settings(DEMO_MODE=True)
class DemoBootstrapTests(TestCase):
    def run_bootstrap(self, username='demo-owner', password='Unique-random-test-926!'):
        with patch.dict('os.environ', {'BOOTSTRAP_ADMIN_USERNAME': username, 'BOOTSTRAP_ADMIN_PASSWORD': password}):
            output = StringIO()
            call_command('bootstrap_demo_admin', stdout=output)
            self.assertNotIn(password, output.getvalue()) if password else None

    def test_creates_admin_and_preserves_changed_password(self):
        self.run_bootstrap()
        user = get_user_model().objects.get(username='demo-owner')
        self.assertTrue(user.is_staff and user.is_superuser)
        self.assertTrue(user.check_password('Unique-random-test-926!'))
        user.set_password('Changed-unique-credential-928!'); user.save()
        self.run_bootstrap()
        user.refresh_from_db()
        self.assertTrue(user.check_password('Changed-unique-credential-928!'))

    def test_refuses_existing_regular_user(self):
        user = get_user_model().objects.create_user(username='demo-owner')
        with self.assertRaises(CommandError): self.run_bootstrap()
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)

    def test_refuses_second_admin(self):
        get_user_model().objects.create_superuser(username='other', password='Other-unique-928!')
        with self.assertRaises(CommandError): self.run_bootstrap()
        self.assertFalse(get_user_model().objects.filter(username='demo-owner').exists())

    @override_settings(DEMO_MODE=False)
    def test_refuses_outside_demo(self):
        with self.assertRaises(CommandError): self.run_bootstrap()

    def test_requires_complete_and_strong_credentials(self):
        for username, password in [('owner', ''), ('', 'secret'), ('owner', '12345678')]:
            with self.assertRaises(CommandError): self.run_bootstrap(username, password)
        self.assertEqual(get_user_model().objects.count(), 0)

    def test_no_credentials_is_noop(self):
        self.run_bootstrap('', '')
        self.assertEqual(get_user_model().objects.count(), 0)

    def test_demo_banner(self):
        response = self.client.get('/entrar/')
        self.assertContains(response, 'Ambiente de demonstração')
        with override_settings(DEMO_MODE=False):
            self.assertNotContains(self.client.get('/entrar/'), 'Ambiente de demonstração')
