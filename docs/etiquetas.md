# Padrão de cadastro e etiquetas

## Código permanente

Novos equipamentos recebem automaticamente **EQ-000001**, **EQ-000002** e assim por diante. A geração é serializada no PostgreSQL, evita colisões e preserva o código em edições posteriores. Não inclua prateleira, cliente ou evento no código: essas informações mudam e possuem campos próprios.

Cadastros anteriores preservam suas etiquetas. A leitura de texto foi padronizada para EQ seguido de seis números; códigos antigos usam QR ou digitação manual. Não apague registros para reutilizar números.

## Como cadastrar

1. Cadastre categorias e localizações com nomes padronizados.
2. Cadastre o modelo e o tipo de controle.
3. Cadastre o equipamento. O código será preenchido ao salvar.
4. Confira série, descrição, conservação e foto.
5. Registre o saldo contado e aprovado em Ajustar saldo.
6. Em **Etiquetas**, selecione os cadastros e gere a impressão.
7. Fixe cada etiqueta no item correto e teste a leitura.

Equipamento individual: uma etiqueta por unidade. Lote: etiqueta no recipiente correspondente e controle por quantidade. Para rastrear cada cabo, cadastre cada um individualmente. Fotografar um case não conta suas peças.

## Modelo implementado

**90 × 40 mm**, com nome da empresa, código grande em fonte monoespaçada, descrição resumida, tipo de controle e QR com margem branca. Preto sobre branco, acabamento fosco e material resistente ao manuseio.

Avalie aderência e durabilidade com a gráfica. Não cubra ventilação, conectores, série do fabricante ou avisos. Em cabos, use um suporte que permaneça legível sem prejudicar a utilização. Não plastifique com material que provoque reflexo sem testar.

Há impressão A4 (duas colunas, em papel adesivo sem gabarito pré-cortado) e térmica de 90 × 40 mm, limitada a 100 etiquetas por seleção. Configure escala 100%, papel correto e sem cabeçalhos/rodapés. Imprima uma unidade, meça e leia antes do lote. Impressoras menores precisam de layout adequado; reduzir tudo pode tornar código/QR ilegível. Códigos antigos muito longos exigem conferência visual do tamanho antes da impressão.

## Identificar por foto

Abra **Identificar por foto**, também disponível dentro do evento. Envie JPEG, PNG ou WebP com até 5 MB e 16 megapixels. Fotografe uma etiqueta por vez, de frente, focada e sem reflexo, ocupando boa parte da imagem.

O sistema tenta primeiro o QR da própria instalação. Caso não o encontre, extrai o texto EQ-000001 com Tesseract. Não identifica pela aparência do equipamento, não adivinha caracteres e não troca O por zero.

Confira número, descrição e equipamento físico antes de abrir a ficha. OCR pode coincidir erroneamente com outro código existente. Havendo múltiplos candidatos, escolha conscientemente; se falhar, recorte a foto ou use o código manual. **A leitura não altera estoque nem cria cadastros.**

As fotos de leitura são processadas no servidor da instalação, sem envio a serviço externo de IA, e não são guardadas permanentemente. Há limite de uma leitura a cada dez segundos por usuário e oito segundos de processamento OCR. Arquivos temporários são removidos pela biblioteca. Fotos de cadastro e avaria têm finalidade e armazenamento privado distintos.

Equipe operacional só consulta equipamentos dos eventos atribuídos. A leitura iniciada dentro de um evento mostra apenas seus itens. Equipamentos desconhecidos devem ser cadastrados antes da impressão: uma foto de número desconhecido não cria patrimônio.

## Endereço de acesso

Configure domínio HTTPS definitivo antes de imprimir. `127.0.0.1` e `localhost` não funcionam no celular para acessar outro computador. Se mudar o domínio, planeje redirecionamento/reimpressão; o código impresso permanece válido.

Câmera ao vivo depende do navegador e de permissão. Enviar uma foto é uma alternativa que não exige a API BarcodeDetector. A operação continua exigindo conexão à internet.
