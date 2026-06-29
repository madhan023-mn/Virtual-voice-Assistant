import base64
from io import BytesIO
from PIL import Image
import os
from openai import OpenAI
import config

cfg = config.get_config()

img = Image.new('RGB', (100, 100), color = 'red')
buf = BytesIO()
img.save(buf, format='JPEG')
buf.seek(0)
base64_image = base64.b64encode(buf.read()).decode('utf-8')
mime_type = "image/jpeg"

client = OpenAI(
    api_key="your_gemini_key_here",
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)
response = client.chat.completions.create(
    model="gemini-1.5-flash",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Describe this image in detail:"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{base64_image}"
                    }
                }
            ]
        }
    ],
    max_tokens=512
)
print("Response:", response.choices[0].message.content.strip())
