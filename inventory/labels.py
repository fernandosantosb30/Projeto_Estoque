"""Identificação por foto: QR primeiro, OCR estrito como alternativa. Sem escrita em estoque."""
import re
from urllib.parse import urlsplit
from uuid import UUID
import warnings
from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image, ImageOps, UnidentifiedImageError

CODE_PATTERN = re.compile(r'(?<![A-Z0-9])EQ\s*[-–—]\s*(\d{6})(?!\d)', re.I)

def qr_token(text):
    """Nunca segue URLs lidas em imagens; reconhece somente formato e origem própria."""
    parts = urlsplit(text.strip())
    base = urlsplit(settings.PUBLIC_BASE_URL)
    if parts.scheme not in ('http','https') or parts.netloc != base.netloc:
        return None
    match = re.fullmatch(r'/equipamento/([0-9a-fA-F-]{36})/', parts.path)
    if not match or parts.query or parts.fragment: return None
    try: return UUID(match.group(1))
    except ValueError: return None

def read_label(upload):
    if upload.size > 5*1024*1024: raise ValidationError('A foto deve ter no máximo 5 MB.')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',Image.DecompressionBombWarning)
            upload.seek(0)
            with Image.open(upload) as original:
                if original.format not in ('JPEG','PNG','WEBP'): raise ValidationError('Envie JPEG, PNG ou WebP.')
                if original.width*original.height > 16_000_000: raise ValidationError('A foto deve ter até 16 megapixels. Recorte a etiqueta.')
                img=ImageOps.exif_transpose(original).convert('RGB')
                img.thumbnail((2200,2200))
    except (UnidentifiedImageError,OSError,Image.DecompressionBombError,Image.DecompressionBombWarning):
        raise ValidationError('Imagem inválida ou grande demais. Fotografe somente a etiqueta.')
    import zxingcpp
    import numpy as np
    results=zxingcpp.read_barcodes(np.asarray(img),formats=zxingcpp.BarcodeFormat.QRCode)
    tokens={token for result in results if (token:=qr_token(result.text))}
    if tokens: return {'tokens':tokens,'codes':set(),'method':'QR Code','warning':''}
    import pytesseract
    if settings.TESSERACT_CMD: pytesseract.pytesseract.tesseract_cmd=settings.TESSERACT_CMD
    gray=ImageOps.autocontrast(ImageOps.grayscale(img))
    try:
        text=pytesseract.image_to_string(gray,lang='eng',config='--psm 11',timeout=8)
    except (pytesseract.TesseractNotFoundError,RuntimeError,pytesseract.TesseractError):
        return {'tokens':set(),'codes':set(),'method':'OCR','warning':'Leitura de texto indisponível ou demorou demais. Use o QR Code ou digite o código.'}
    # Não troca O por 0, não completa dígitos e não aproxima códigos.
    codes={f'EQ-{number}' for number in CODE_PATTERN.findall(text)}
    return {'tokens':set(),'codes':codes,'method':'Texto da etiqueta (OCR)','warning':''}
