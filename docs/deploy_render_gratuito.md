# Demonstração gratuita — Render + Neon

Use esta configuração para apresentar o sistema com dados fictícios. Ela não contrata disco nem banco no Render. O arquivo `render.yaml` continua sendo a opção paga; **para esta demonstração escolha `render.demo.yaml`**.

## Informações para preparar

| Informação | Onde usar |
| --- | --- |
| Repositório GitHub com esta versão e branch desejada | Conectar ao Render |
| Conta Render com plano Free disponível | Hospedar o sistema |
| Projeto Neon Free exclusivo para a demonstração | Guardar cadastros e movimentações |
| URL de conexão PostgreSQL do Neon | Variável secreta `DATABASE_URL` no Render |
| Nome da empresa na apresentação | `COMPANY_NAME` |
| Nome e senha exclusiva do administrador | `BOOTSTRAP_ADMIN_USERNAME` e `BOOTSTRAP_ADMIN_PASSWORD` |

Não envie senhas no chat nem as salve no GitHub. Preencha-as diretamente no painel do Render. Não reutilize o banco nem as credenciais de produção.

## 1. Banco no Neon

1. Crie um projeto no plano Free, com PostgreSQL 17 quando disponível e região próxima de Virginia (US East), escolhida para o serviço web.
2. Abra **Connect** e copie a connection string **direta**, sem pooling, para esta instalação pequena. Ela começa por `postgresql://` e contém usuário, senha, host e banco.
3. Preserve os parâmetros de segurança fornecidos pelo Neon, incluindo `sslmode=require`. Cole somente a URL, sem `psql`, aspas ou comandos de terminal.
4. Guarde-a para preencher `DATABASE_URL` no Render. Não a publique em arquivos ou screenshots.

## 2. Código no GitHub

Envie a versão revisada do projeto, incluindo Dockerfile, `render.demo.yaml`, scripts e migrations. `.env`, `.demo-access.txt`, fotos e backups devem permanecer fora do repositório. Prefira um repositório privado.

A CI executa testes e construção do Docker. Aguarde o resultado antes da apresentação. Não importe automaticamente os dados da sua máquina: o Neon começa vazio e recebe as tabelas durante o primeiro startup.

## 3. Criar no Render

1. Acesse **New → Blueprint**, conecte o repositório e escolha a branch com esta versão.
2. No campo de caminho do Blueprint, selecione **`render.demo.yaml`**.
3. Preencha as quatro variáveis solicitadas: URL Neon, empresa, usuário e senha inicial.
4. Confira o resumo: somente **um Web Service Free**, sem banco Render e sem disco. Se aparecer recurso pago, revise o arquivo selecionado antes de continuar.
5. Crie o serviço e acompanhe os logs. A imagem Docker instala Python, bibliotecas e Tesseract. O startup aplica migrações e cria o administrador inicial.
6. Abra a URL HTTPS atribuída pelo Render. `/healthz/` deve responder `ok`; em `/entrar/`, entre com as credenciais escolhidas.
7. Após confirmar o login, exclua **ambas** as variáveis `BOOTSTRAP_ADMIN_USERNAME` e `BOOTSTRAP_ADMIN_PASSWORD` do painel e aplique a atualização. A conta continua no banco. Inicializações seguintes não trocam sua senha.

Não há senha padrão. Se a conta inicial já existir como administrador ativo, a senha é preservada. O comando recusa promover uma conta comum ou criar outro administrador quando já existe um. Gerencie novas contas no `/admin/` após entrar. Guarde sua senha em um gerenciador; o plano Free não oferece shell remoto e este projeto ainda não tem recuperação por e-mail.

### Valores já configurados no arquivo

| Variável | Valor |
| --- | --- |
| `DJANGO_DEBUG` | `0` |
| `DEMO_MODE` | `1` |
| `DJANGO_SECRET_KEY` | Gerada automaticamente pelo Render |
| `MEDIA_ROOT` | `/var/data/media` — temporário, **sem disco montado** |
| `WEB_CONCURRENCY` | `1` |
| `GUNICORN_THREADS` | `1` |
| `OMP_THREAD_LIMIT` | `1` |

O hostname HTTPS do Render configura automaticamente o endereço público, hosts permitidos e origem CSRF. Não configure `localhost` ou `127.0.0.1` nessas opções no Render. Não altere o segredo a cada deploy.

O runtime é **Docker**, não Python nativo. O Dockerfile fornece os comandos de inicialização; não é necessário preencher Build/Start Command. Deploy automático está desativado; atualizações exigem deploy manual no painel.

## 4. Preparar a apresentação

- Cadastre categoria, localização, modelo, equipamento e saldo inicial, usando exemplos fictícios.
- Cadastre um cliente fictício e simule três eventos simultâneos para mostrar disponibilidade e reservas.
- Imprima uma etiqueta e teste QR e foto com o celular na URL HTTPS publicada.
- Teste saída, devolução e conferência com os perfis adequados.
- Abra o site alguns minutos antes da reunião e confirme login e banco.

O perfil usa um processo e uma thread para reduzir consumo de memória. A leitura de foto pode atrasar outras requisições enquanto é processada. O desempenho de OCR em 512 MB precisa ser medido no Render; não há garantia de latência. Se a leitura falhar, use QR ou consulte o código manualmente.

## Limites e persistência

O Render Free suspende por inatividade após 15 minutos e pode levar cerca de um minuto para voltar. Arquivos locais enviados desaparecem em reinícios, suspensões ou deploys. O diretório `/var/data/media` **não é persistente nesta configuração**, apesar do nome. Fotos devem ser reenviadas; cadastros e movimentações permanecem no Neon enquanto o banco estiver disponível e dentro dos limites do plano. A foto usada apenas para identificação já é descartada pelo sistema.

A página mostra um aviso de demonstração. Não carregue o patrimônio real do cliente antes de configurar armazenamento permanente, backup e monitoramento. Para manter fotos nesta demo seria necessária outra integração de armazenamento privado.

A gratuidade depende das cotas de ambos os provedores. Confira consumo e opções de cobrança no painel; não habilite upgrade automático para esta apresentação. O arquivo não configura banco gratuito do Render, que expira após 30 dias.

## Diagnóstico rápido

- Erro de conexão: revise a URL Neon, senha, banco, TLS e disponibilidade do projeto.
- Erro de administrador: confira as duas variáveis, força da senha e se o banco já tem administrador.
- HTTP 400/CSRF: retire hosts de localhost e confirme o domínio HTTPS efetivo.
- Memória/OCR: teste imagem menor ou QR; consulte logs antes de prometer leitura rápida.
- Foto sumiu: comportamento esperado do disco efêmero; reenvie a foto de demonstração.

## Fontes

- [Limites gratuitos do Render](https://render.com/docs/free)
- [Blueprint e caminho do YAML](https://render.com/docs/blueprint-spec)
- [Django com Neon](https://neon.com/blog/python-django-and-neons-serverless-postgres)

Preparação local não equivale a publicação: contas, conexão Neon, build Docker e teste no domínio real precisam ser concluídos no provedor.
