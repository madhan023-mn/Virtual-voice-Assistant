import requests
from io import BytesIO
from PIL import Image

# create a dummy image
img = Image.new('RGB', (100, 100), color = 'red')
buf = BytesIO()
img.save(buf, format='JPEG')
buf.seek(0)

res = requests.post("http://127.0.0.1:5000/api/upload/image", files={"file": ("test.jpg", buf, "image/jpeg")})
print("Status:", res.status_code)
print("Response:", res.json())
