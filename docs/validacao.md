# Validação da entrega

Este documento registra a entrega inicial. Para a preparação de produção, etiquetas e reconhecimento por foto, consulte [Validação para Render](validacao_render.md).

Data: 14/09/2026. Ambiente: Python 3.14.4, Django 5.2.17 e PostgreSQL 18.6 local isolado.

## Resultados

- `manage.py check`: sem problemas.
- `manage.py makemigrations --check --dry-run`: sem mudanças pendentes.
- `manage.py test inventory --verbosity 1`: **26 testes aprovados**, em 18,667 segundos na execução final.
- Compilação dos módulos Python e verificação de sintaxe JavaScript: aprovadas.
- Demonstração: 11 cadastros de equipamentos/lotes, 3 eventos simultâneos e 12 linhas de planejamento. As seis caixas foram distribuídas entre os três eventos sem repetição de unidade.
- Navegador: login real, painel, detalhes do evento e layout de 390 × 844 conferidos. Localização manual por código abriu a unidade correta. Separação, saída e devolução foram registradas pela interface; a devolução manteve uma unidade aguardando conferência. As demais operações completas, inclusive manutenção/liberação, foram verificadas na suíte.
- QR: geração autenticada testada. Câmera física não exercitada; depende de HTTPS, permissão e suporte do navegador. Há alternativa manual verificada.
- Backup com aplicação parada: arquivo PostgreSQL, arquivo de mídia e manifesto gerados; hashes validados; restauração em banco separado aprovada. Conferidos 11 equipamentos, 3 eventos, 12 linhas e 29 registros de auditoria no instante do backup. O acervo demo não possuía fotos nesse momento; o tratamento de upload temporário e referência compartilhada de avaria foi testado separadamente na suíte.

## Cobertura relevante

Reservas concorrentes de uma mesma unidade; três eventos com lotes compartilhados; intervalos contíguos e disjuntos; cancelamento; composição de kits e rollback de kit incompleto; substituição; alteração de datas; expedição condicionada à separação; retorno parcial; liberação após conferência; bloqueio de manutenção; atraso afetando disponibilidade futura; consumo sem dupla reserva; perdas; dispensa autorizada de quantidade não expedida; ajuste auditado; perfis, visibilidade da equipe, CSRF e proteção contra fórmula em CSV.

## Ambiente de demonstração

O PostgreSQL local está em `/tmp/palco-pg-data`, porta 55432 e socket `/tmp/palco-pg-socket`. É temporário e pode não sobreviver à limpeza de `/tmp`. O endereço local da aplicação é http://127.0.0.1:8000. A conta de demonstração está no arquivo privado `.demo-access.txt`, excluído do versionamento.

O evento Congresso Conexões contém as movimentações fictícias feitas na revisão do navegador. Há uma caixa devolvida aguardando conferência para experimentar a próxima etapa. Os outros dois eventos continuam reservados.

Para reiniciar neste computador, enquanto o diretório temporário existir, inicie o PostgreSQL se necessário:

```bash
/usr/lib/postgresql/18/bin/pg_ctl -D /tmp/palco-pg-data -l /tmp/palco-pg.log -o '-k /tmp/palco-pg-socket -p 55432 -h 127.0.0.1' start
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

## Limites de validação

Nenhuma publicação, configuração de domínio/HTTPS ou rotina agendada de backup foi feita. A validação não é teste de carga com o volume real da empresa e não inclui câmera em aparelho físico ou restauração em infraestrutura de produção. O README e o manual registram os limites funcionais desta versão.
