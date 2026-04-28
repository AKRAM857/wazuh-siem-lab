# Wazuh AI Alert Analyzer
# Reads last 10 alerts from Wazuh and analyzes them using local Ollama LLM
# Requirements: Ollama running locally with llama3.2 model
# Usage: python3 wazuh_ai.py


import urllib.request
import json
all_alerts_text=""
with open('#path to alert file','r',encoding='utf-8') as file:
     lines=file.readlines()
     last_alerts=lines[-10:]
     for line in last_alerts:
       alert=json.loads(line)
       id_L=alert['rule'].get('mitre',{})
       f_log = alert['full_log']
       timestamp = alert['timestamp']
       technique = alert['rule'].get('mitre', {}).get('technique', 'N/A')
       all_alerts_text += f"Time: {timestamp} | What happened: {f_log} |id of machine: {id_L}| Technique: {technique}\n"

message = f"""
You are a security analyst. Here are the last 10 security alerts from our system.
Analyze them together and tell me:
1. What attack is happening?
2. Who is the attacker?
3. How serious is it?
4. What should we do?

Alerts:
{all_alerts_text}
"""

data = json.dumps({
    "model": "llama3.2",
    "prompt": message,
    "stream": False
}).encode()

req = urllib.request.Request(
    "http://localhost:11434/api/generate",
    data=data,
    headers={"Content-Type": "application/json"})

response = urllib.request.urlopen(req)
result = json.loads(response.read())
print(result['response'])
