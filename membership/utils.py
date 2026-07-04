from io import BytesIO

import qrcode
from django.core.files.base import ContentFile


def make_qr_file(payload, filename):
    image = qrcode.make(payload)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return ContentFile(buffer.getvalue(), name=filename)
