#!/usr/bin/env bash
set -euo pipefail
# O volume montado pode pertencer a root; ajuste só o diretório de fotos e reduza privilégios.
mkdir -p "${MEDIA_ROOT:-/var/data/media}"
chown palco:palco "${MEDIA_ROOT:-/var/data/media}"
chmod 700 "${MEDIA_ROOT:-/var/data/media}"
exec gosu palco "$@"
