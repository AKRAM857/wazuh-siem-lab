# Wazuh SIEM Lab — Troubleshooting and Setup

## What is this project?

Wazuh is an open source security platform that combines 
XDR and SIEM capabilities. It collects, analyzes, and 
correlates security events from monitored systems and 
presents them in a dashboard.

The platform has 3 main components:
- **Agent** — installed on endpoints, collects logs and events
- **Manager** — the brain, receives data from agents and generates alerts
- **Indexer** — the database, stores all alerts for search and visualization
- **Dashboard** — the interface where you see everything

## Goal of this lab

Set up a complete Wazuh deployment on Ubuntu, connect a 
Kali Linux attack machine as a monitored agent, simulate 
a brute force SSH attack, and detect it in the dashboard.
## Lab Architecture

### Virtual Machines
- **Ubuntu 25.10** — Wazuh Server + Router + DHCP Server
- **Kali Linux 2025.4** — Attack machine + Wazuh Agent

### Network Interfaces (Ubuntu)
| Interface | IP | Role |
|-----------|-----|------|
| enp0s3 | 10.0.2.15 | NAT - internet access |
| enp0s8 | 192.168.20.1 | Gateway for VLAN 1 (Kali) |
| enp0s9 | 192.168.10.1 | Gateway for VLAN 2 |

### Network Diagram
Internet | [Ubuntu - Router/DHCP/Wazuh Server] | | [OVS Bridge] [OVS Bridge] | | VLAN 1 VLAN 2 | Kali Linux (192.168.20.21)
### Why this design matters for Wazuh
Because Ubuntu controls all traffic from Kali:
- All Kali's network activity passes through Ubuntu
- Ubuntu's Wazuh agent sees everything Kali does
- Attacks from Kali land directly on Ubuntu's SSH
- This makes detection more reliable and realistic
### Design Decision — Why OVS and VLANs?

In a flat network, all machines can communicate freely 
with no control. By making Ubuntu the router and gateway:

1. **Security** — Ubuntu can block or filter any traffic 
   from Kali at any time using firewall rules (ufw, iptables)

2. **Segmentation** — Each VLAN is isolated. A compromised 
   machine in VLAN 1 cannot directly reach VLAN 2

3. **Realism** — In real enterprises, networks are always 
   segmented. Attackers have to move laterally between 
   segments — this lab simulates that

4. **Control** — As the router, Ubuntu sees ALL traffic. 
   This makes Wazuh detection more effective since nothing 
   bypasses the monitoring point
## Installation

### Ubuntu (Wazuh Server)
- **Wazuh Manager** —the brain that analyzes data that come from the agents.
- **Wazuh Indexer** — the database where data lives
- **Wazuh Dashboard** — the interface that shows results
- **Filebeat OSS 7.10.2** — moves data from the manager to the indexer

### Kali Linux
- **Wazuh Agent** — a sensor in kali that sends data to the manager in ubuntu

### Important versions
- Wazuh: v4.14.4
- Filebeat: OSS 7.10.2 (must match indexer version)
- OpenSearch/Indexer: 7.10.2
## Problems Faced and Solutions

---

### Problem 1 — Wazuh Manager Timeout on Restart
**Symptom:** `systemctl restart wazuh-manager` timed out
**Cause:** Manager takes long to stop gracefully due to active connections
**Fix:**
```bash
systemctl kill -s SIGKILL wazuh-manager
sleep 5
systemctl start wazuh-manager
```
**Lesson:** Use SIGKILL to force stop a service that won't stop gracefully

---

### Problem 2 — wazuh-install.yml Corrupted
**Symptom:** File contained AWS XML error instead of credentials
**Cause:** During installation a download from Wazuh's S3 bucket failed and the error response was saved as the file
**Impact:** Admin password was lost
**Fix:** Reset password directly using the passwords tool

---

### Problem 3 — Dashboard Password Unknown
**Symptom:** Couldn't login to dashboard
**Fix:**
```bash
/usr/share/wazuh-indexer/plugins/opensearch-security/tools/wazuh-passwords-tool.sh -u admin -p NewPassword123.
```
**Lesson:** Password must contain a symbol from this set only: `.*+?-`

---

### Problem 4 — log_format Was Plain
**Symptom:** Alerts generated in alerts.log but indexer count = 0
**Cause:** Wazuh was writing alerts in plain text. Indexer needs JSON format to parse and store alerts
**Fix:** In `/var/ossec/etc/ossec.conf`:
```xml
<logging>
  <log_format>plain,json</log_format>
</logging>
```
**Verify:**
```bash
ls /var/ossec/logs/alerts/
# Should show both alerts.log AND alerts.json
```

---
---

### Problem 5— Filebeat Version Incompatibility
**Symptom:**
**Cause:** Installed Filebeat 8.x but Wazuh Indexer runs on OpenSearch 7.10.2. Version mismatch.
**Fix:** Remove Filebeat 8.x, install Filebeat **OSS** 7.10.2
**Why OSS:** Regular Filebeat checks for an Elastic license. OpenSearch doesn't have one. OSS version has no license checks.

---

### Problem 6 — Config Corrupted by Markdown (Root Cause of Most Issues)
**Symptom:** Multiple fixes not working, config had corrupted values:
**Cause:** Claude.ai chat converts certain text into markdown hyperlinks. Copy-pasting from chat wrote those links into the config file.
**Fix:** Use Python to write the config directly, bypassing copy-paste:
```bash
python3 << 'PYEOF'
config = """..clean config here.."""
with open('/etc/filebeat/filebeat.yml', 'w') as f:
    f.write(config)
PYEOF
```
**Lesson:** Never copy config files directly from a chat or web page. Always verify with:
```bash
filebeat test config
filebeat test output
```

---

### Problem 7 — Wrong Index Mapping
**Symptom:**
**Cause:** First failed Filebeat attempts created an index with wrong field mappings. The schema got locked and rejected all new data.
**Fix:**
1. Add processor to drop conflicting fields in filebeat.yml:
```yaml
processors:
  - drop_fields:
      fields: ["host", "agent", "ecs", "input", "log"]
```
2. Delete the corrupted index:
```bash
curl -k --cert /etc/wazuh-indexer/certs/admin.pem \
     --key /etc/wazuh-indexer/certs/admin-key.pem \
     -X DELETE "https://127.0.0.1:9200/wazuh-alerts-*"
```

---

### Problem 8 — Harvester Not Starting
**Symptom:** Filebeat running, no errors, but no data flowing
**Cause:** Registry pointed to end of file from previous failed runs
**Fix:**
```bash
systemctl stop filebeat
rm -rf /var/lib/filebeat/registry
systemctl start filebeat
```
**What is the registry:** Filebeat's memory of where it last read in each file. If it points to the end, Filebeat thinks there's nothing new to read.
## Attack Detection Test

### Goal
Validate that the complete Wazuh pipeline works end-to-end —
from attack detection to dashboard visualization.

### Attack Executed
- **Tool:** Hydra (brute force SSH tool)
- **From:** Kali Linux (192.168.20.21)
- **Target:** Ubuntu SSH service (192.168.20.1)
- **Method:** Dictionary attack using rockyou.txt wordlist

### How Detection Works
Hydra sends thousands of SSH login attempts to Ubuntu.
Ubuntu's SSH service logs every attempt to auth.log.
Wazuh Manager reads auth.log and generates alerts.
Filebeat ships alerts to the Indexer.
Results appear in the Dashboard.
### Results
| Metric | Count |
|--------|-------|
| Total alerts | 44,000+ |
| Authentication failures | 44,000+ |
| Authentication successes | 14 |

### MITRE ATT&CK Detected
- T1110 — Brute Force
- T1110.001 — Password Guessing
- T1021.004 — SSH

### What Surprised Me
14 successful authentications were recorded during the attack.
This could mean:
- Normal logins during the test period
- Hydra accidentally guessing a correct password
- Worth investigating in a real environment

### Lesson
Even a basic brute force attack is immediately visible in Wazuh.
In a real SOC, this would trigger an investigation instantly.
### The Detection Pipeline
Kali (Hydra) → sends SSH login attempts → Ubuntu SSH service
                                                |
                                          SSH writes to
                                          /var/log/auth.log
                                                |
                                    Wazuh Manager reads auth.log
                                                |
                                    Generates alert in alerts.json
                                                |
                                         Filebeat ships to indexer
                                                |
                                            Dashboard

## Lessons Learned

### Documentation
- Never work without documenting in real time — 
  going back to reconstruct what you did is painful and incomplete
- Document the WHY not just the WHAT — 
  commands without context are useless later

### Technical
- Always verify a fix worked before moving to the next step (Rule 4 — verify don't assume)
- Read error messages carefully — the solution is often inside the error itself (Filebeat told us to use OSS version)
- Understand the pipeline before touching anything — know which component talks to which
- Version compatibility matters — Filebeat 8.x broke everything, OSS 7.10.2 fixed it
- Test config before starting a service (`filebeat test config && filebeat test output`)

### Mindset
- Don't assume — verify with commands
- Change ONE thing at a time, then test
- Logs tell the truth — always read them before trying fixes
- A symptom is not the root cause — we fixed registry, index, harvester but the real problem was the corrupted config the whole time

### Networking and Security
- network without security is like a sheap around wolfs

## Final Thoughts
this project is very important to me cuz this is my first time i use documentation and it's my first step in devsecops domain, i am planning to develop it more by adding automation and docker and a lot of things
