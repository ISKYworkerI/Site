from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile


def compress_image(image, quality=85):
    img = Image.open(image)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    output = BytesIO()
    img.save(output, format='JPEG', quality=quality)
    output.seek(0)
    return InMemoryUploadedFile(output, 'ImageField', 
                                image.name, 'image/jpeg', output.getbuffer().nbytes, None)
