# wazuh-siem-lab
# Wazuh SIEM Lab

## Overview
Wazuh open source XDR/SIEM deployed on Ubuntu, monitoring 
a Kali Linux attack machine over a custom OVS/VLAN network.

## Infrastructure
Built on top of → [Network Lab](your-network-repo-link)

## Stack
| Component | Version |
|-----------|---------|
| Wazuh | v4.14.4 |
| Filebeat OSS | 7.10.2 |
| OpenSearch | 7.10.2 |
| Ubuntu | 25.10 |
| Kali Linux | 2025.4 |

## Architecture
Internet → Ubuntu (Router/DHCP/Wazuh Server)
|
OVS Bridge
|
Kali Linux (Agent)
## What Was Tested
- Hydra SSH brute force from Kali → Ubuntu
- 44,000+ alerts generated
- MITRE ATT&CK: T1110 Brute Force detected

## Key Problems Solved
1. Filebeat OSS 7.10.2 required (not standard 8.x)
2. log_format must be plain,json not plain
3. Index mapping corruption — deleted and recreated
4. Config corruption from copy-paste — used Python to write config

## Full Documentation
See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for detailed 
problems, fixes, and lessons learned.

## Lessons Learned
- Document in real time, not at the end
- Never copy configs from chat — corruption happens
- Read logs before trying fixes
- Verify every fix before moving to the next step
