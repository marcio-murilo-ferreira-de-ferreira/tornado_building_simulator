import os

d = os.path.expanduser("~/.streamlit")
os.makedirs(d, exist_ok=True)

# Delete existing corrupted files if any
config_path = os.path.join(d, "config.toml")
creds_path = os.path.join(d, "credentials.toml")

if os.path.exists(config_path):
    os.remove(config_path)
if os.path.exists(creds_path):
    os.remove(creds_path)

# Write proper utf-8 config files
with open(config_path, "w", encoding="utf-8") as f:
    f.write("[browser]\ngatherUsageStats = false\n")
    
with open(creds_path, "w", encoding="utf-8") as f:
    f.write("[general]\nemail = \"\"\n")

print("Streamlit configuration fixed!")
