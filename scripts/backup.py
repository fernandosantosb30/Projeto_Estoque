#!/usr/bin/env python3
"""Backup consistente: execute sem escritores (janela de manutenção)."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from urllib.parse import urlsplit, unquote, parse_qs
import tarfile
from datetime import datetime, timezone
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parents[1]
load_dotenv(ROOT/'.env')
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--destination',required=True)
parser.add_argument('--writers-stopped',action='store_true',help='Confirma que a aplicação está parada para obter banco e arquivos coerentes.')
args=parser.parse_args()
if not args.writers_stopped:parser.error('Pare os processos de escrita e informe --writers-stopped.')
os.umask(0o077)
folder=Path(args.destination).expanduser().resolve()/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
folder.mkdir(parents=True,exist_ok=False)
env=os.environ.copy()
for source,target,default in [('POSTGRES_DB','PGDATABASE','palco'),('POSTGRES_USER','PGUSER','palco'),('POSTGRES_PASSWORD','PGPASSWORD',''),('POSTGRES_HOST','PGHOST','127.0.0.1'),('POSTGRES_PORT','PGPORT','5432')]:env[target]=os.environ.get(source,default)
if os.environ.get('DATABASE_URL'):
    url=urlsplit(os.environ['DATABASE_URL'])
    env.update(PGHOST=url.hostname or '',PGPORT=str(url.port or 5432),PGUSER=unquote(url.username or ''),PGPASSWORD=unquote(url.password or ''),PGDATABASE=unquote(url.path.lstrip('/')))
    options=parse_qs(url.query)
    if 'sslmode' in options: env['PGSSLMODE']=options['sslmode'][0]
media=Path(os.environ.get('MEDIA_ROOT',str(ROOT/'media'))).expanduser().resolve()
if media==folder or media in folder.parents: raise SystemExit('O destino do backup não pode ficar dentro de MEDIA_ROOT.')
subprocess.run(['pg_dump','--format=custom','--file',str(folder/'database.dump')],env=env,check=True)
with tarfile.open(folder/'media.tar.gz','w:gz') as archive:
    if media.exists():archive.add(media,arcname='media')
manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'files':{}}
for name in ['database.dump','media.tar.gz']:
    manifest['files'][name]=hashlib.file_digest((folder/name).open('rb'),'sha256').hexdigest()
(folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(folder/'COMPLETE').write_text('Backup finalizado. Teste a restauração antes de depender desta cópia.\n')
print(f'Backup concluído: {folder}')
