import paramiko
import sys
import socket

def handler(title, instructions, prompts):
    print("PROMPTS:", prompts)
    return ["dummy"] * len(prompts)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("submit.hpc.psu.edu", 22))

t = paramiko.Transport(sock)
t.start_client()
print("Available:", t.auth_publickey)

try:
    t.auth_interactive("testuser", handler)
except Exception as e:
    print("Error:", str(e))
