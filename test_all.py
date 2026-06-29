import requests
import json
import base64
from io import BytesIO
from PIL import Image
import os

BASE_URL = "http://127.0.0.1:5000"

def test_chat(message):
    print(f"Testing Chat: {message}")
    res = requests.post(f"{BASE_URL}/api/chat", json={"message": message, "session_id": "test_session"})
    if res.status_code != 200:
        print(f"  ERROR {res.status_code}: {res.text}")
    else:
        print(f"  SUCCESS: {res.json().get('text')[:100]}...")

def test_image():
    print("Testing Image Upload...")
    img = Image.new('RGB', (100, 100), color = 'blue')
    buf = BytesIO()
    img.save(buf, format='JPEG')
    buf.seek(0)
    res = requests.post(f"{BASE_URL}/api/upload/image", files={"file": ("test.jpg", buf, "image/jpeg")}, data={"session_id": "test_session"})
    if res.status_code != 200:
        print(f"  ERROR {res.status_code}: {res.text}")
    else:
        print(f"  SUCCESS: {res.json().get('text')[:100]}...")

def test_document():
    print("Testing Document Upload...")
    res = requests.post(f"{BASE_URL}/api/upload/document", files={"file": ("test.txt", b"This is a test document.", "text/plain")}, data={"session_id": "test_session"})
    if res.status_code != 200:
        print(f"  ERROR {res.status_code}: {res.text}")
    else:
        print(f"  SUCCESS: {res.json().get('text')[:100]}...")

def test_interview():
    print("Testing Mock Interview...")
    res = requests.post(f"{BASE_URL}/api/interview/start", json={"resume_text": "Software Engineer with 5 years of Python experience.", "session_id": "test_session"})
    if res.status_code != 200:
        print(f"  ERROR {res.status_code}: {res.text}")
    else:
        print(f"  SUCCESS: {res.json().get('text')[:100]}...")

if __name__ == "__main__":
    try:
        requests.get(f"{BASE_URL}/api/health")
    except requests.exceptions.ConnectionError:
        print("Server is not running. Please start it on port 5000 first.")
        exit(1)
        
    test_chat("Hello ARIA, what is the capital of France?")
    test_chat("play some music on youtube")
    test_image()
    test_document()
    test_interview()
    test_chat("What is my name?")
    print("All tests finished.")
