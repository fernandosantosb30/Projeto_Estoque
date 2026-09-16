"""Valida backup/restauração em banco novo, exclusivamente no ambiente local."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import uuid
import psycopg
from psycopg import sql
from django.conf import settings
from django.core.management import BaseCommand, CommandError
from inventory.models import Asset,Event,EventLine,Audit
class Command(BaseCommand):
    help='Com o servidor parado, cria backup e restaura em banco novo de verificação local.'
    def handle(self,*args,**kwargs):
        if not settings.DEBUG:raise CommandError('Somente desenvolvimento.')
        counts={m._meta.db_table:m.objects.count() for m in [Asset,Event,EventLine,Audit]}
        destination=Path('/tmp')/('palco-backup-check-'+uuid.uuid4().hex[:8])
        subprocess.run([sys.executable,str(settings.BASE_DIR/'scripts/backup.py'),'--destination',str(destination),'--writers-stopped'],check=True)
        folder=next(destination.iterdir())
        manifest=json.loads((folder/'manifest.json').read_text())
        for name,digest in manifest['files'].items():
            with (folder/name).open('rb') as f:
                if hashlib.file_digest(f,'sha256').hexdigest()!=digest:raise CommandError('Hash divergente.')
        with tarfile.open(folder/'media.tar.gz') as archive:archive.getmembers()
        db=settings.DATABASES['default']
        restored='palco_restore_'+uuid.uuid4().hex[:8]
        args={'host':db['HOST'],'port':db['PORT'],'user':db['USER'],'password':db['PASSWORD']}
        with psycopg.connect(dbname='postgres',autocommit=True,**args) as conn:
            conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(restored)))
        env=os.environ.copy()
        env.update(PGHOST=db['HOST'],PGPORT=str(db['PORT']),PGUSER=db['USER'],PGPASSWORD=db['PASSWORD'])
        subprocess.run(['pg_restore','--no-owner','--no-acl','--exit-on-error','--dbname',restored,str(folder/'database.dump')],env=env,check=True)
        with psycopg.connect(dbname=restored,**args) as conn:
            for table,count in counts.items():
                actual=conn.execute(sql.SQL('SELECT count(*) FROM {}').format(sql.Identifier(table))).fetchone()[0]
                if actual!=count:raise CommandError(f'Divergência em {table}.')
        self.stdout.write(self.style.SUCCESS(f'Backup, hashes e restauração validados: {counts}. Banco separado: {restored}. Backup: {folder}'))
