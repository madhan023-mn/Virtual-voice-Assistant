import os
import sys

# Append venv path if needed or just run with vvoice python
sys.path.append(os.path.dirname(__file__))

import config
cfg = config.get_config()

from assistant import _chat_with_groq

print("Groq Key:", cfg.GROQ_API_KEY)
if not cfg.GROQ_API_KEY:
    print("NO KEY")
    sys.exit(1)

history = []
msg = "hw ru"

try:
    res = _chat_with_groq(history, msg)
    print("Response:", res)
except Exception as e:
    print("ERROR:", str(e))
