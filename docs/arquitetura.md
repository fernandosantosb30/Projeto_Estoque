# Arquitetura e premissas

- Uma empresa, um banco PostgreSQL e aplicação Django 5.2 LTS. Não há isolamento multiempresa.
- Estrutura modular: models define dados e invariantes, services executa mutações transacionais, access aplica perfis, forms valida entrada, views e templates expõem os fluxos.
- Reservas usam janela [retirada, liberação). O calendário é diário e mostra ambos os dias como contexto.
- Um bloqueio consultivo transacional PostgreSQL serializa todas as mutações operacionais. Para cerca de três eventos simultâneos, escolhemos simplicidade e correção acima de maior paralelismo. O banco usa o isolamento padrão READ COMMITTED. Todos os caminhos de escrita de saldo, reserva, kit e manutenção usam o mesmo bloqueio; não altere esses dados diretamente via SQL ou scripts externos. Django Admin é somente leitura para os dados operacionais.
- A disponibilidade por quantidade usa varredura de extremos; não soma reservas disjuntas. Unidades físicas têm saldo máximo 1 validado no serviço. O banco protege contagens de linhas, unicidade evento/equipamento, quantidades e ordem temporal.
- Previsão futura considera liberação planejada. Quando ela vence, materiais ainda fora/aguardando conferência passam a bloquear qualquer nova janela até regularização. Expedição sempre verifica saldo físico além da reserva.
- Manutenção aberta bloqueia a quantidade até liberação explícita, independentemente da previsão.
- Kits são modelos de composição copiados para as linhas; cada adição é incremental, consolidada por equipamento, com origem registrada. Não há estoque virtual de kit.
- Baixas reduzem patrimônio; dispensas reduzem obrigação de expedir sem apagar planejamento ou inventar saída.
- Auditoria não é editável pela interface. Não é um log criptograficamente imutável contra administradores de banco. A trilha de catálogo registra os valores salvos, mas não implementa uma comparação campo a campo antes/depois.
- Fotografias passam por ImageField, limite de 5 MB e formatos JPEG/PNG/WebP. Arquivos são servidos por endpoint autenticado, nunca por MEDIA_URL pública. Em produção, não exponha media diretamente no servidor web.
- QR é URL opaca autenticada; BarcodeDetector é melhoria opcional, com alternativa manual. Não envia imagens a serviços externos.
- Bootstrap é distribuído localmente com licença MIT no cabeçalho do arquivo.
- Dados demo e banco em /tmp são apenas ambiente de desenvolvimento, nunca a infraestrutura definitiva do cliente.

## Fora do escopo

Financeiro, contratos, fiscal, multiempresa, materiais de terceiros, frota, notificações externas e offline. A versão também não tem importação em massa, paginação, estorno operacional genérico, edição de datas depois da primeira saída. Esses limites estão no manual. Volumes elevados pedem paginação, otimização de consultas e medição de carga antes de expansão.

## Referências técnicas

- Django 5.2 LTS: https://docs.djangoproject.com/en/5.2/releases/5.2/
- Transações: https://docs.djangoproject.com/en/5.2/topics/db/transactions/
- Bloqueios consultivos PostgreSQL: https://www.postgresql.org/docs/current/explicit-locking.html#ADVISORY-LOCKS


## Preparação de produção e etiquetas

Docker/Blueprint para Render, uma instalação por empresa, com WhiteNoise e fotos em disco privado persistente. Novos códigos EQ são gerados dentro do serviço serializado e imutáveis pela interface. Fotos são lidas por ZXing-C++ e Tesseract, sem serviços externos. OCR exige conferência humana. Formulários de movimentação incluem UUID persistido na auditoria contra reenvio duplicado. Limitação de leituras usa cache compartilhado no banco. Login utiliza django-axes por conta, sem confiar em IP informado pelo cliente.
