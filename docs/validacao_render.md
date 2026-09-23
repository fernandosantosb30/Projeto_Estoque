# Validação da preparação para Render — 22/09/2026

## Escopo verificado

- Suíte completa: **41 testes aprovados**, em 37,960 segundos, com `manage.py test --settings=config.test_settings --noinput`. A configuração de testes usa hash rápido somente para contas fictícias; produção mantém o hash seguro do Django.
- `makemigrations --check --dry-run`: nenhuma alteração de modelo sem migração.
- Cadastro com código automático `EQ-000001`, preservação de códigos antigos e impressão A4/térmica de 90 × 40 mm.
- Leitura real de QR e OCR de código em imagens sintéticas; confirmação humana, limites de upload e alternativa manual.
- Proteção contra reenvio da mesma movimentação e correção de saída de outros itens após devolução com avaria.
- Migrações aplicadas em PostgreSQL temporário e separado dos dados do cliente.
- `check --deploy --fail-level WARNING` com DEBUG desativado: aprovado.
- `collectstatic --noinput`: aprovado, 130 arquivos e 363 processamentos. Removida referência a mapa de código inexistente no Bootstrap que impedia a coleta.
- Teste integrado com configurações de produção: páginas, impressão térmica, CSS com hash, foto privada com controle de acesso, healthcheck e redirecionamento HTTPS aprovados.
- `pip check`, sintaxe dos scripts shell e `git diff --check`: aprovados.

Os testes locais usam Python 3.14 e PostgreSQL 18. A instalação das dependências fixadas também foi verificada com Python 3.12. O Docker e a CI estão configurados para Python 3.12 e PostgreSQL 17.

## Limites desta validação

Não houve publicação no Render nem execução remota da CI. O Docker não foi construído localmente porque o ambiente não disponibiliza Docker. A primeira homologação deve confirmar construção da imagem, permissões/persistência do disco, proxy HTTPS, memória e restauração de backup. Nenhum serviço pago foi criado.

As imagens de teste não substituem a leitura de etiquetas físicas sob iluminação e desgaste reais. Imprima uma amostra em escala 100% e valide com o celular da equipe. Defina o domínio final antes de imprimir o lote.

O sistema é destinado a uma empresa por instalação. Backup externo, retenção e monitoramento operacional precisam ser configurados antes de colocar dados reais em produção.

Consulte [Publicação no Render](deploy_render.md) e [Etiquetas](etiquetas.md).
