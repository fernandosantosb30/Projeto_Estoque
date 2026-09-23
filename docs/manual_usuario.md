# Manual de utilização · Palco

Este manual descreve a versão entregue. A aplicação controla materiais próprios para eventos, com reservas por período, movimentações e manutenção. Use o menu **Ajuda e manual** para consultar ou imprimir este documento.

## 1. Primeiro acesso e perfis

O administrador cria as contas em **Administração → Usuários**, define uma senha inicial e atribui **um** grupo por pessoa. Para acessar o admin, a conta precisa da opção de equipe administrativa (staff); conceda acesso administrativo apenas a quem gerencia usuários. Superusuários têm acesso completo. Os grupos operacionais não exigem staff.

- **Administrador:** todas as operações; usuários e configurações pelo admin com as permissões administrativas adequadas.
- **Gestor:** cadastros, eventos, reservas, substituições, ajustes, baixa por perda, dispensa de itens não expedidos e relatórios.
- **Estoque:** consulta, separação, saída, recebimento, conferência, consumo e manutenção. Não confirma reservas, cancela eventos ou aprova perdas.
- **Equipe operacional:** consulta eventos em que está na equipe ou é responsável e registra ocorrências. Não altera saldos.

Entre com usuário e senha em `/entrar/`. O administrador pode redefinir senhas pelo admin. Não há recuperação por e-mail implementada. Não compartilhe contas: cada ação precisa ter autor identificável. Para sair, use **Sair da conta**; em celular, a opção fica ao final da página.

## 2. Preparar os cadastros

1. Em **Modelos e categorias → Categorias**, cadastre Sonorização, Estruturas de palco e Acessórios, por exemplo.
2. Em **Localizações**, cadastre endereços físicos como `Depósito A · Corredor 01 · Prateleira 02`.
3. Em **Modelos e categorias**, crie cada especificação: nome, categoria, tipo de controle, marca e modelo. Informe mínimo para consumíveis.
4. Em **Equipamentos → Novo cadastro**, vincule uma unidade ou lote ao modelo e local. O código EQ-000001 é gerado automaticamente. Preencha série, conservação e foto opcional. Compra e valor são opcionais; em lote, o valor informado é do cadastro como um todo.
5. Abra a ficha do equipamento e use **Ajustar saldo**. Informe a quantidade contada como diferença positiva e a justificativa `Inventário inicial conferido em ... por ...`.
6. Confira o relatório de patrimônio antes de operar.

Um equipamento **individual** aceita saldo 0 ou 1, com um cadastro por unidade. Um item **por quantidade** representa unidades equivalentes no mesmo local. Materiais com especificação ou localização diferente devem usar outro lote. **Consumíveis** podem ser baixados por consumo.

Não altere o tipo de controle de um modelo que já possui equipamentos, nem troque o modelo de um equipamento com saldo ou histórico. Crie um novo cadastro quando a especificação for outra. Para retirar um cadastro de uso, desmarque **Ativo**. A inativação não apaga histórico e pode gerar conflitos em reservas existentes, visíveis no painel.

## 3. Etiquetas e QR Code

Abra a ficha do equipamento e clique em **Imprimir ficha / etiqueta**. O navegador permite imprimir ou salvar em PDF. A ficha inclui código legível, descrição e QR. Para etiquetas em lote, abra **Etiquetas**, selecione os itens e escolha A4 ou térmica de 90 × 40 mm. Imprima a 100%, sem cabeçalhos.

O QR contém somente o endereço de identificação com identificador opaco. O acesso aos dados exige login e permissão. O administrador técnico deve configurar `PUBLIC_BASE_URL` para o endereço acessível aos celulares antes de imprimir etiquetas definitivas; `localhost` não funciona em outro dispositivo.

Na operação de um evento, use **Localizar etiqueta neste evento**. Digite o código e clique em **Localizar item**, ou clique em **Ler com câmera**. A leitura localiza a linha, mas não confirma movimentações automaticamente: escolha operação e quantidade e registre.

A câmera depende de HTTPS, autorização e suporte do navegador à API BarcodeDetector. Quando não houver suporte, o sistema orienta usar o código manual. Também é possível ler a etiqueta com a câmera externa do celular, abrir a ficha e acessar o evento. Não há operação offline.

## 4. Clientes e eventos

1. Em **Clientes**, cadastre nome, contato e observações.
2. Em **Agenda e eventos → Novo evento**, informe cliente, local, responsável e equipe.
3. Preencha retirada, montagem, início, término, retorno e liberação após conferência.
4. Salve como rascunho. Adicione equipamentos avulsos ou kits.
5. Consulte **Disponibilidade** para o intervalo completo, antes de confirmar.
6. Clique em **Confirmar reserva**. Corrija conflitos apontados, selecionando outras unidades ou alterando o período antes da saída.

A sequência deve ser retirada ≤ montagem ≤ início < término ≤ retorno ≤ liberação. A reserva ocupa o intervalo da retirada até a liberação, sem incluir o instante final. Portanto, uma reserva que termina às 10h pode ser seguida por outra às 10h, mas programe folga operacional realista.

Rascunhos não reservam estoque. A confirmação bloqueia unidades e quantidades. O calendário mostra os dias atravessados pela janela inteira, inclusive a data de liberação; a lista pode abranger outros meses, conforme seus filtros. Filtre por responsável, situação, texto e intervalo.

O sistema permite editar datas e cadastro até a primeira saída, revalidando reservas confirmadas. Após a primeira saída, registre mudanças operacionais como ocorrência; a alteração de datas nessa fase não está implementada. Atrasos são tratados automaticamente pelo saldo físico e pelos alertas.

## 5. Kits e substituições

1. Abra **Kits → Novo cadastro** e crie um nome operacional.
2. Clique em **Componentes**. Selecione modelo e quantidade. Clique em editar na composição para mudar uma linha existente.
3. No evento, selecione o kit e clique em **Adicionar composição do kit**.

O sistema escolhe unidades/lotes com capacidade no período, consolida linhas por equipamento e acrescenta as quantidades. Cada inclusão é adicional: clicar duas vezes solicita dois conjuntos. Se faltar qualquer componente, toda a inclusão do kit é desfeita. O botão não reutiliza material já solicitado como se fosse novo saldo.

A composição fica copiada no evento; alterar o kit não altera eventos anteriores. A origem das inclusões é exibida nos detalhes do item. Kits de palco são listas de materiais, sem validação técnica estrutural.

Antes da saída, abra o item do evento → **Ajustar quantidade ou substituir**. Selecione equipamento, quantidade final e justificativa. A separação daquele item será zerada para nova conferência. Um substituto já presente no evento deve ser ajustado na própria linha, não duplicado.

Para dispensar quantidades não expedidas em evento ativo, o gestor usa **Dispensar quantidade não expedida**, com justificativa. O planejamento original e a dispensa ficam registrados. Isso permite resolver uma saída parcial autorizada sem simular movimentações.

## 6. Separação e saída

1. Abra **Separação e saídas** e selecione o evento.
2. Use a lista organizada por categoria e localização. Imprima a lista, se necessário.
3. Inicie a separação ou registre a operação **Registrar separação** em cada item.
4. Conte os materiais, confira etiquetas e registre a quantidade efetivamente separada.
5. No carregamento, selecione **Registrar saída**, informe a quantidade liberada e registre.
6. Imprima a lista/comprovante atualizado. O histórico identifica quem separou e quem liberou.

É possível separar e expedir em etapas. A saída não pode ultrapassar a quantidade separada, o planejamento restante ou o saldo físico. A mesma unidade não pode estar em duas saídas ativas. Equipamentos em manutenção impedem saída e podem afetar reservas futuras.

Não use a saída para apenas “testar” o sistema em dados reais. Movimentações não são apagadas; treine no banco de demonstração.

## 7. Retorno, avarias e pendências

1. Abra **Devoluções** e entre no evento.
2. Em cada item, selecione **Receber devolução**, quantidade e condição recebida. Adicione foto opcional quando necessário.
3. Leve o material à área física de conferência. O recebimento ainda não libera o saldo.
4. Após testar e contar, selecione **Conferir e liberar**, com quantidade e condição final.
5. Para defeitos, escolha **Conferir com avaria → manutenção**. Uma ordem corretiva é aberta automaticamente para a quantidade informada.
6. Repita em devoluções parciais, inclusive em datas diferentes.
7. O gestor conclui o evento somente quando não houver itens por expedir sem dispensa, retornos ou conferências pendentes.

**Exemplo:** saíram 6 cabos, chegaram 4 e 3 foram conferidos. O sistema mostra 2 a retornar e 1 a conferir. Apenas os 3 conferidos voltam ao saldo físico disponível.

**Consumíveis:** registre **Consumo** para a quantidade utilizada e devolução/conferência para o restante. **Perdas:** o gestor registra **Baixa por perda** com justificativa, apenas para material expedido ainda não devolvido. Isso reduz o patrimônio e mantém o registro. Itens recebidos devem ser conferidos; descarte de material no depósito é feito por ajuste autorizado quando não houver bloqueios.

Um retorno atrasado ou sem conferência não é liberado pela passagem do tempo. Após a liberação prevista vencida, os itens ainda retidos bloqueiam o planejamento futuro até a regularização. Confira os alertas no painel e no evento.

## 8. Manutenção

Em **Manutenção → Abrir manutenção**, selecione equipamento, quantidade, tipo, motivo, prestador, previsão, custo e foto opcional. Só pode abrir diretamente uma quantidade fisicamente disponível; para retornos avariados use a conferência do evento.

A manutenção aberta bloqueia a quantidade sem presumir liberação na data prevista. Reservas existentes afetadas aparecem nos alertas. Ao terminar, registre condição final, testes e custo, e clique em **Concluir e liberar para uso**. Uma ordem fechada não pode ser liberada novamente. O histórico contém o responsável.

A versão aceita anexos de imagem JPEG, PNG e WebP, até 5 MB; PDFs e anexos genéricos não estão implementados.

## 9. Painel, relatórios e inventário

- **Disponível no depósito:** soma de total menos quantidades em operação/conferência e manutenção, excluindo cadastros inativos. É saldo físico atual, sem descontar reservas futuras.
- **Em eventos:** expedido menos retornado e baixado.
- **Aguardando conferência:** retornado menos conferido.
- **Em manutenção:** quantidades em ordens abertas.
- **Consumível abaixo do mínimo:** soma física disponível do modelo menor que o mínimo cadastrado.
- **Disponibilidade por período:** menor capacidade restante ao longo do intervalo, considerando reservas sobrepostas, manutenções abertas e retenções atrasadas. Reservas que não se sobrepõem não são somadas indevidamente.

Os indicadores somam unidades e quantidades de lotes; não representam número de modelos diferentes ou valor patrimonial.

Em **Relatórios**, selecione patrimônio, movimentações, equipamentos por evento, pendências, manutenção ou utilização. Use **Exportar CSV** para planilhas ou **Imprimir** para impressão/PDF pelo navegador.

Patrimônio mostra a posição atual e ignora o filtro temporal. Movimentações usam a data do registro. Manutenção usa a data de abertura. Eventos, pendências e utilização incluem eventos cuja janela cruza o período. Utilização conta eventos com saída e quantidades expedidas nesses eventos, não dias em uso ou percentual de ocupação. Não representa somente as saídas ocorridas dentro das datas filtradas.

Para inventário, compare o relatório de patrimônio com a contagem física e as quantidades em eventos, conferência e manutenção. Registre a diferença aprovada na ficha do equipamento, nunca uma troca silenciosa do saldo.

## 10. Erros frequentes e correções

**“Existe no depósito, mas não consigo reservar.”** Consulte a agenda, manutenção e retornos sem conferência. Saldo físico e disponibilidade futura são diferentes.

**“O kit está incompleto.”** Abra sua composição, consulte o período e disponibilize todos os componentes ou ajuste a composição antes de adicioná-la.

**“O retorno atrasou e compromete outro evento.”** Registre ocorrência, comunique o gestor e substitua o item do evento futuro antes da saída. O alerta permanece até resolver o bloqueio.

**“Preciso cancelar.”** O gestor cancela antes da primeira saída; reservas são liberadas e o evento permanece no histórico. Depois da saída, conclua os retornos ou registre perdas/dispensas justificadas.

**“Cadastrei saldo errado.”** Faça um ajuste com a diferença e a justificativa. Reduções que violam obrigações físicas ou reservas são rejeitadas.

**“Registrei saída ou retorno errado.”** Registre imediatamente uma ocorrência e procure o gestor. Esta versão não possui estorno genérico de movimentações. Não simule consumo, perda ou retorno para ocultar o erro. A correção de histórico operacional indevido exige análise técnica auditada e backup prévio.

**“Não consigo concluir.”** Verifique itens ainda não expedidos, retornos e conferências. O gestor pode dispensar itens não expedidos com justificativa ou baixar perdas reais. Não existe encerramento que apague pendências.

## 11. Limites desta versão

Sem financeiro completo, emissão fiscal, orçamento/contrato comercial, sublocação de terceiros, múltiplas empresas, notificações externas, uso offline, importação em massa, estorno genérico ou edição de datas após primeira saída. Alertas são internos ao sistema. Cadastros possuem páginas de 40 itens; relatórios e agenda ainda não são paginados; avalie desempenho com o volume real antes da implantação. A leitura de câmera depende do navegador. Não há exclusão operacional de históricos; desative cadastros.


## Novos códigos e identificação por foto

Novos cadastros recebem códigos EQ-000001 em sequência; os antigos são preservados. Use **Identificar por foto** para ler o QR ou o código EQ impresso. Confirme o resultado antes de operar. A leitura não movimenta estoque. Consulte o [guia de etiquetas](/ajuda/?doc=etiquetas) para tamanhos, limites e procedimento.
