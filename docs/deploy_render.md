# Publicação no Render

Para apresentar sem mensalidade, siga [Demonstração gratuita com Neon](deploy_render_gratuito.md) e selecione `render.demo.yaml`. Este guia abaixo descreve a instalação paga com fotos persistentes.

Esta versão contém Dockerfile e Blueprint para **uma empresa por instalação**. Para outro cliente, crie outro serviço, banco, disco, segredo e domínio. Grupos de usuários não isolam empresas dentro do mesmo banco.

## Configuração preparada

- Python 3.12, Gunicorn, PostgreSQL, WhiteNoise e Tesseract no Docker.
- `render.yaml`: serviço web pago (`1c-2g`), PostgreSQL 17 pago (`0.1c-256mb`) e disco de 10 GB para fotos. Revise os preços e planos no painel antes de criar recursos.
- Migrações, cache, perfis e estáticos executados na inicialização. Uma falha interrompe o startup.
- Healthcheck `/healthz/`, HTTPS por proxy, cookies seguros, CSRF e limite de tentativas de login.
- OCR no próprio servidor; fotos de identificação não são armazenadas permanentemente nem enviadas a serviços de IA.
- Deploy automático desativado; publique após testes e backup.

## 1. Repositório e criação

Revise e envie as alterações para um repositório privado. Não versione `.env`, `.demo-access.txt`, `.venv`, fotos ou backups. `.gitignore` e `.dockerignore` já os excluem.

A CI em `.github/workflows/ci.yml` testa PostgreSQL 17, OCR, configuração de produção e construção do Docker quando executada no GitHub. A existência do arquivo não significa que a execução remota já ocorreu.

No Render:

1. Selecione **New → Blueprint** e conecte o repositório.
2. Selecione a branch revisada e `render.yaml`.
3. Informe `COMPANY_NAME`, usado nas etiquetas.
4. Confira recursos, região e preços; confirme a contratação somente após essa revisão.
5. Acompanhe o deploy. No fim, `/healthz/` deve retornar `ok`.

O Render fornece `DATABASE_URL` pela rede interna e gera o segredo. Seu segredo base64 de 256 bits é convertido deterministicamente pelo aplicativo para o comprimento esperado pelo Django. Preserve o segredo entre publicações para não invalidar sessões.

O disco fica em `/var/data`, com fotos em `/var/data/media`. O entrypoint prepara as permissões e executa o servidor como usuário sem privilégios. Não use `/app/media` em produção: arquivos fora do disco são efêmeros.

A proposta tem **uma instância**, com disco local e uma breve interrupção durante deploys. Não habilite múltiplas instâncias sem migrar fotos para armazenamento privado de objetos e rever a arquitetura. O plano gratuito de web service não suporta esse desenho com disco persistente. Monitore memória, latência e espaço: o plano indicado é um ponto de partida, não garantia para qualquer volume.

## 2. Administrador e usuários

No Shell do serviço, execute:

```bash
python manage.py createsuperuser
```

Use credenciais exclusivas para o cliente. Não importe a conta de demonstração. Em `/admin/`, crie contas individuais e atribua um perfil. Staff/permissões administrativas são necessários para administrar usuários; estoque e equipe operacional não precisam de staff.

Após cinco falhas, a conta fica bloqueada por 15 minutos. Para desbloquear pelo Shell:

```bash
python manage.py axes_reset_username NOME_DO_USUARIO
```

O bloqueio é por conta, sem confiar em IP informado pelo navegador. Não há recuperação por e-mail. Para redefinir senha, use o admin ou `python manage.py changepassword USUARIO`.

## 3. Endereço antes de imprimir etiquetas

Sem domínio próprio, a aplicação usa o hostname HTTPS fornecido pelo Render. Para domínio próprio, configure-o no provedor e defina:

```text
PUBLIC_BASE_URL=https://estoque.suaempresa.com.br
DJANGO_ALLOWED_HOSTS=estoque.suaempresa.com.br
DJANGO_CSRF_TRUSTED_ORIGINS=https://estoque.suaempresa.com.br
```

O hostname do Render continua permitido automaticamente. Valide HTTPS antes de imprimir: o QR contém o endereço. Se trocar domínio, mantenha o antigo redirecionando ou reimprima as etiquetas. A leitura por foto aceita QR da origem configurada; o código textual continua válido.

Nunca entregue etiquetas com `127.0.0.1` ou `localhost` ao cliente.

## 4. Homologação no ambiente contratado

Antes de carregar patrimônio real:

- Teste login no computador e em celular físico.
- Cadastre um equipamento e confira seu código automático EQ-000001.
- Registre saldo inicial, imprima em escala 100%, meça e teste a etiqueta no depósito.
- Teste QR e OCR, conferindo o resultado sem presumir leitura perfeita.
- Simule eventos sobrepostos, saída e devolução parcial, conferência e manutenção.
- Teste uma repetição do mesmo envio de movimentação e confira que não duplica o registro.
- Envie uma foto de cadastro, publique novamente e confirme persistência e acesso privado.
- Teste cada perfil e restaure um backup em banco separado.

A preparação local não substitui essa homologação: ela confirma permissões do volume, proxy, custos e desempenho efetivo do provedor.

## 5. Backup

O script lê `DATABASE_URL` e `MEDIA_ROOT`, além das variáveis locais antigas. O cliente PostgreSQL do Docker deve permanecer compatível com a versão 17 do banco definido no Blueprint; revise-o ao atualizar a versão principal.

Em uma janela sem gravações, coloque o serviço em manutenção no Render e confirme que operações em andamento terminaram. Execute no Shell:

```bash
python scripts/backup.py --destination /var/data/backups --writers-stopped
```

`--writers-stopped` declara que você já interrompeu escritores; não bloqueia operações sozinho. A rotina gera dump, arquivo de fotos e hashes SHA-256, marcando COMPLETE somente no sucesso.

Copie a pasta para outro destino protegido. **Backup somente no mesmo disco não protege contra perda desse disco.** Backups do PostgreSQL do provedor não incluem as fotos. Combine retenção, cópia externa e alertas antes de operar. Nenhum agendamento ou destino externo foi contratado/configurado automaticamente.

O README explica restauração em banco novo. Não restaure primeiro por cima da base ativa. Preserve também configuração e versão do código por meio seguro; o backup não inclui `.env`.

## 6. Atualizações e diagnóstico

Teste, faça backup e revise migrações antes de publicar. `requirements.lock.txt` fixa dependências; atualize deliberadamente e repita a validação. Falhas de inicialização são exibidas nos logs: conexão, migração, estáticos, OCR ou volume. O healthcheck verifica banco, mas não substitui monitoramento de memória, disco e backups.

O serviço com disco exige uma janela de manutenção em deploys. Não prometa atualização sem interrupção ou operação offline. Os limites funcionais estão no manual.

## Fontes oficiais consultadas

- https://render.com/docs/deploy-django
- https://render.com/docs/blueprint-spec
- https://render.com/docs/disks
- https://render.com/docs/deploys
