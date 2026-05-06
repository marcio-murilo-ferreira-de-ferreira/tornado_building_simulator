import paramiko
import sys
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
try:
    print("Connecting...")
    client.connect("submit.hpc.psu.edu", username="testuser", password="badpassword", timeout=10)
except Exception as e:
    t = client.get_transport()
    if t:
        try:
            t.auth_none("testuser")
        except paramiko.BadAuthenticationType as exc:
            print(f"Allowed types: {exc.allowed_types}")
    print("Exception:", str(e))
