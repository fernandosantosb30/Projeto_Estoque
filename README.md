> **Preparação para nuvem e etiquetas:** veja [Deploy no Render](docs/deploy_render.md) e [Padrão de etiquetas](docs/etiquetas.md). Uma empresa por instalação. A publicação real e contratação dos recursos ainda não foram realizadas.

> **Apresentação gratuita:** use [Render Free + Neon](docs/deploy_render_gratuito.md) com `render.demo.yaml`. O `render.yaml` padrão prevê recursos pagos.

# Palco · Gestão de equipamentos por evento

Aplicação Django para uma empresa de sonorização e palcos, com reservas, kits, expedição, devolução, manutenção, auditoria, relatórios e ajuda integrada. Interface em português, responsiva, com Bootstrap local. PostgreSQL é obrigatório, inclusive nos testes de concorrência.

## Iniciar

Requisitos: Python 3.12–3.14, PostgreSQL 14 ou superior e cliente PostgreSQL (`pg_dump`, `pg_restore`). A versão foi exercitada com Python 3.14, Django 5.2.17 e PostgreSQL 18.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
.venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(50))'
```

Copie a chave gerada para DJANGO_SECRET_KEY. Edite `.env` com um banco PostgreSQL e usuário próprios, criados pelo administrador do servidor. O usuário da aplicação precisa poder criar tabelas nesse banco; use uma conta de teste separada com CREATEDB para executar os testes. Não use superusuário PostgreSQL em produção.

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py setup_roles
.venv/bin/python manage.py createcachetable
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Abra http://127.0.0.1:8000 e entre com a conta criada. Use `/admin/` para usuários e atribuição de grupos. Os modelos operacionais são somente leitura no admin para proteger regras; os cadastros são feitos pelas telas próprias.

## Configuração

| Variável | Uso |
|---|---|
| DJANGO_SECRET_KEY | Segredo aleatório, obrigatório, nunca versionado |
| DJANGO_DEBUG | 1 somente no desenvolvimento; 0 em produção |
| DJANGO_ALLOWED_HOSTS | Lista de nomes/IPs permitidos, separados por vírgula |
| POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD | Banco e credenciais |
| POSTGRES_HOST, POSTGRES_PORT | Servidor e porta; também aceita diretório de socket local |
| PUBLIC_BASE_URL | URL acessível aos usuários, incorporada nas etiquetas QR |
| DJANGO_SECURE_SSL_REDIRECT | 1 em produção com HTTPS corretamente configurado |

O ambiente tem prioridade sobre `.env`. Horários usam America/Sao_Paulo; Django armazena com fuso. Sessões/CSRF usam cookies seguros quando DEBUG=0. Não exponha `media/` publicamente.

## Demonstração

Em banco de teste sem eventos, após criar um administrador:

```bash
.venv/bin/python manage.py seed_demo --username SEU_USUARIO
```

São criados três eventos simultâneos, seis caixas individuais distribuídas sem duplicação, cabos por quantidade, treliças individuais, consumíveis e um kit. Não há senha embutida nem criação automática de contas no seed. Não execute em dados reais; a demonstração se recusa a rodar se já houver eventos.

Abra os três eventos e confira as unidades vinculadas. Em um deles, separe e expeça materiais, faça um retorno parcial e observe a pendência. Receba o restante, confira parte como bom e parte como avariado. Confira o bloqueio em Manutenção. Registre consumo e retorno das fitas. Libere a manutenção e conclua o evento quando todas as pendências estiverem resolvidas.

## Testes e verificações

```bash
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test inventory --settings=config.test_settings --verbosity 2
```

A suíte cria `test_<POSTGRES_DB>`. Nunca aponte testes a uma instância de produção. Inclui transações em conexões independentes para duas reservas concorrentes, intervalos sobrepostos/disjuntos, três eventos, kits, ajustes, saída e retorno parcial, avarias, manutenção, perdas, consumo, dispensa de expedição, permissões, CSRF, CSV e renderização das telas.

## Implantação

1. Providenciar servidor e PostgreSQL persistente com credenciais próprias, fora de `/tmp`.
2. Configurar domínio, HTTPS, variáveis e permissões de arquivos. Usar DEBUG=0 e uma chave exclusiva.
3. Executar migrações, setup_roles e criar administrador.
4. Executar `collectstatic --noinput` e servir `staticfiles/` no proxy. Arquivos privados continuam atrás do endpoint Django.
5. Executar `gunicorn config.wsgi:application --bind 127.0.0.1:8000` sob gerenciador de serviços; encaminhar pelo proxy HTTPS. Configure indicação de HTTPS por proxy somente quando ele remover cabeçalhos enviados pelo cliente e definir os próprios; o exemplo não confia em cabeçalhos de proxy por padrão.
6. Executar `manage.py check --deploy` com configuração final; revisar HSTS depois de HTTPS validado.
7. Testar login, permissões, câmera em dispositivos reais e o fluxo completo com a equipe.
8. Configurar e testar backups e restauração antes de carregar o patrimônio real.

Esta entrega não publica serviço, contrata hospedagem, configura domínio ou agenda backup de produção. O servidor Django de desenvolvimento não é apropriado para internet pública.

## Backup

A rotina inclui banco PostgreSQL, imagens e manifesto SHA-256. Para coerência entre banco e arquivos, pare os processos de escrita durante a execução. Agende uma janela sem operação.

```bash
.venv/bin/python scripts/backup.py --destination /CAMINHO/SEGURO/backups --writers-stopped
```

O parâmetro declara que você já parou a aplicação; o script não a para. Ele só cria `COMPLETE` após sucesso. Diretórios incompletos não são backups válidos. Faça cópia para destino separado, restrito e preferencialmente criptografado. `.env` e código não fazem parte do arquivo: mantenha configuração protegida e versão do código separadamente.

Para agendar em produção, o administrador deve criar um timer do sistema ou job no agendador de sua infraestrutura que: pare os escritores, execute a rotina com destino persistente, verifique código de saída/COMPLETE, copie o backup para outro destino, volte a iniciar o serviço inclusive em falha e alerte o suporte. Configure retenção conforme a empresa; o script não apaga backups automaticamente. Nenhum agendamento foi instalado nesta entrega.

### Restaurar com segurança

1. Escolha backup com COMPLETE e valide hashes do manifest.json.
2. Pare a aplicação. Preserve a base atual antes de qualquer restauração.
3. Crie um **novo banco vazio** e restaure: `pg_restore --no-owner --no-acl --exit-on-error --dbname=NOME_DO_NOVO_BANCO /backup/database.dump`, usando PGHOST, PGPORT, PGUSER e credencial segura/pgpass.
4. Inspecione e extraia `media.tar.gz` em diretório temporário privado. Use apenas arquivos de backup confiáveis; copie a pasta media para o destino da aplicação com as permissões do usuário do serviço.
5. Aponte a configuração de teste ao banco restaurado, mantenha o código correspondente ao backup e execute `manage.py check`.
6. Confira totais, eventos, históricos e imagens; teste login e leitura.
7. Só depois da validação planeje a troca do banco em produção e reinício. Nunca restaure diretamente por cima do banco ativo como primeiro teste.

## Documentos

- [Manual de utilização](docs/manual_usuario.md)
- [Guia de organização da empresa](docs/guia_operacional.md)
- [Arquitetura, premissas e limites](docs/arquitetura.md)

O manual e o guia também estão em Ajuda. Consulte os limites antes de adoção: não há estorno genérico, alteração de datas após primeira saída, importação em massa ou paginação de relatórios. Perfis de aplicação não substituem proteção do banco e da infraestrutura.

## Avaliação preparada neste computador

O ambiente local já possui dados fictícios. Consulte `.demo-access.txt` para entrar e [Validação da entrega](docs/validacao.md) para resultados e instruções de reinício do PostgreSQL temporário. Para reproduzir exatamente as dependências verificadas, utilize `requirements.lock.txt`. Não use o banco temporário nem a conta de demonstração na operação real da empresa.
# Projeto_Estoque


## Leitura de fotos

Além das dependências Python, instale Tesseract e inglês para códigos alfanuméricos. Em Debian/Ubuntu: `sudo apt-get install tesseract-ocr tesseract-ocr-eng fonts-dejavu-core`. O Dockerfile já inclui esses pacotes. TESSERACT_CMD permite caminho personalizado. A suíte usa Tesseract real e DejaVuSansMono-Bold; execute com `--settings=config.test_settings`. Em produção, o cache é compartilhado no PostgreSQL e os estáticos usam manifesto WhiteNoise.
