from .settings import *
STORAGES={**STORAGES,'staticfiles':{'BACKEND':'django.contrib.staticfiles.storage.StaticFilesStorage'}}
CACHES={'default':{'BACKEND':'django.core.cache.backends.locmem.LocMemCache'}}
# Testes exercitam autenticação sem o custo do hash de produção por fixture.
PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
