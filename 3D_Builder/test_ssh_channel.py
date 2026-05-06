import paramiko
import sys
import os

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
print("Testing channel open...")
try:
    # Ler a senha do app.py temporariamente
    import re
    app_text = open("app.py", "r", encoding="utf-8").read()
    # Pega direto do Streamlit se a senha tiver guardada (Não consegue pq ta no navegador)
    pass
except Exception:
    pass
