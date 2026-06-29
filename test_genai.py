from PIL import Image
from io import BytesIO
from google import genai
import config

cfg = config.get_config()
client = genai.Client(api_key=cfg.GEMINI_API_KEY)

img = Image.new('RGB', (100, 100), color = 'red')
response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents=[img, 'Describe this image.']
)
print(response.text)
