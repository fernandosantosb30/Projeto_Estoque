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
DEMO_MODE = os.environ.get('DEMO_MODE', '0') == '1'
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

# Produção: Render usa URL de banco, proxy HTTPS e disco persistente privado.
import dj_database_url
from urllib.parse import urlsplit
from datetime import timedelta
if os.environ.get('DATABASE_URL'):
    DATABASES['default'] = dj_database_url.parse(os.environ['DATABASE_URL'],conn_max_age=60,conn_health_checks=True)
    if not DATABASES['default']['ENGINE'].endswith('postgresql'):
        raise ImproperlyConfigured('DATABASE_URL deve usar PostgreSQL.')
DATABASES['default'].setdefault('OPTIONS',{}).update(connect_timeout=10)
RENDER = os.environ.get('RENDER','').lower() == 'true'
render_host=os.environ.get('RENDER_EXTERNAL_HOSTNAME','')
if render_host:
    ALLOWED_HOSTS.append(render_host)
    if not os.environ.get('PUBLIC_BASE_URL'): PUBLIC_BASE_URL='https://'+render_host
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS if h.strip()]
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS',PUBLIC_BASE_URL).split(',') if o.strip()]
MEDIA_ROOT = Path(os.environ.get('MEDIA_ROOT',str(BASE_DIR/'media')))
COMPANY_NAME=os.environ.get('COMPANY_NAME','Palco')
TESSERACT_CMD=os.environ.get('TESSERACT_CMD','')
MIDDLEWARE.insert(1,'whitenoise.middleware.WhiteNoiseMiddleware')
STORAGES={'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
if not DEBUG:
    # O segredo gerado pelo Render tem 256 bits em base64 (44 caracteres).
    if RENDER and 32 <= len(SECRET_KEY) < 50:
        import hashlib
        SECRET_KEY=hashlib.sha256(SECRET_KEY.encode()).hexdigest()
    if len(SECRET_KEY)<50 or SECRET_KEY.startswith('gere-'):
        raise ImproperlyConfigured('Produção exige DJANGO_SECRET_KEY aleatória com pelo menos 50 caracteres.')
    if '*' in ALLOWED_HOSTS: raise ImproperlyConfigured('Não use curinga em ALLOWED_HOSTS.')
    if urlsplit(PUBLIC_BASE_URL).scheme!='https': raise ImproperlyConfigured('PUBLIC_BASE_URL deve usar HTTPS em produção.')
    if RENDER and not os.environ.get('MEDIA_ROOT'): raise ImproperlyConfigured('Configure MEDIA_ROOT; use disco persistente na operação real.')
    SECURE_SSL_REDIRECT=True
    SECURE_HSTS_SECONDS=int(os.environ.get('DJANGO_HSTS_SECONDS','3600'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS=True
    SECURE_HSTS_PRELOAD=True
SECURE_REDIRECT_EXEMPT=[r'^healthz/$']
# Render controla o proxy externo. Outros provedores devem habilitar explicitamente.
if RENDER or os.environ.get('TRUST_PROXY_HTTPS')=='1':
    SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')
SECURE_REFERRER_POLICY='same-origin'
SESSION_COOKIE_AGE=8*60*60
INSTALLED_APPS.append('axes')
MIDDLEWARE.append('axes.middleware.AxesMiddleware')
AUTHENTICATION_BACKENDS=['axes.backends.AxesStandaloneBackend','django.contrib.auth.backends.ModelBackend']
AXES_FAILURE_LIMIT=5
AXES_COOLOFF_TIME=timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS=[['username','ip_address']]
AXES_RESET_ON_SUCCESS=True
AXES_CLIENT_IP_CALLABLE=lambda request: None
AXES_LOCKOUT_TEMPLATE='registration/locked.html'
CACHES={'default':{'BACKEND':'django.core.cache.backends.db.DatabaseCache','LOCATION':'palco_cache','TIMEOUT':60}}
LOGGING={'version':1,'disable_existing_loggers':False,'handlers':{'console':{'class':'logging.StreamHandler'}},'root':{'handlers':['console'],'level':'INFO'},'loggers':{'axes':{'level':'WARNING'}}}
