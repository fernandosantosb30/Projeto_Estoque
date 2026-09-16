import os
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '')
if not SECRET_KEY:
    raise ImproperlyConfigured('Configure DJANGO_SECRET_KEY no ambiente ou .env.')
DEBUG = os.environ.get('DJANGO_DEBUG', '0') == '1'
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
INSTALLED_APPS = ['django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'inventory']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages','inventory.access.navigation']}}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': {'ENGINE':'django.db.backends.postgresql','NAME':os.environ.get('POSTGRES_DB','palco'),'USER':os.environ.get('POSTGRES_USER','palco'),'PASSWORD':os.environ.get('POSTGRES_PASSWORD',''),'HOST':os.environ.get('POSTGRES_HOST','127.0.0.1'),'PORT':os.environ.get('POSTGRES_PORT','5432')}}
AUTH_PASSWORD_VALIDATORS = [{'NAME': 'django.contrib.auth.password_validation.'+v} for v in ['UserAttributeSimilarityValidator','MinimumLengthValidator','CommonPasswordValidator','NumericPasswordValidator']]
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR/'static']
STATIC_ROOT = BASE_DIR/'staticfiles'
MEDIA_ROOT = BASE_DIR/'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
LOGIN_URL = '/entrar/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/entrar/'
PUBLIC_BASE_URL = os.environ.get('PUBLIC_BASE_URL','http://127.0.0.1:8000').rstrip('/')
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 8 * 1024 * 1024
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT','0') == '1'
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
