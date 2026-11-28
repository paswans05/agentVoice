# Asterisk 23 External SIP Trunk Setup Guide

## 1. Architecture Overview

AgentVoice separates **internal SIP/WebRTC extensions** (`1001`, `1002`, `1001-ws`, `1002-ws`, `600`, `700` in `[from-internal]`) from **external carrier SIP trunks** (`[sip-trunk-external]` using `[from-trunk-external]` and `[to-trunk-external]`).

- **Internal calling** works locally on Docker Desktop with zero external providers.
- **External PSTN calling** requires mounting or rendering [pjsip_trunk.conf.template](file:///d:/open-source/agentVoice/docker/asterisk/pjsip_trunk.conf.template) with authorized carrier credentials.

---

## 2. Authentication Modes Supported

1. **`userpass_registration`**: Uses `outbound_auth` + `registration` (`SIP_TRUNK_USER`, `SIP_TRUNK_PASSWORD`, `SIP_TRUNK_HOST`).
2. **`ip_whitelist`** (e.g., Exotel vSIP): Uses `[sip-trunk-external-identify]` matching the carrier IP/FQDN; omit `[sip-trunk-external-reg]`.
3. **`digest_challenge`**: Uses `outbound_auth` without `registration`.

---

## 3. NAT, TLS, and RTP Firewall Rules (VPS Production)

When deploying on a public VPS:
1. Set `external_media_address` and `external_signaling_address` in `[transport-external-udp]` / `[transport-external-tcp]` to your VPS public IP.
2. Open **UDP/TCP 5060** (or **TCP 5070** / **TLS 5061/443** depending on carrier) **restricted to your SIP carrier's IP ranges only** (never open SIP/ARI `8088` to `0.0.0.0/0`).
3. Open **UDP 10000–20000** (or `10000–40000` for Exotel) for RTP media.
4. Keep ARI (`8088`) bound to `127.0.0.1` or the private Docker network (`agentvoice-api` -> `asterisk:8088`).

---

## 4. Verification Commands

```bash
# Verify Asterisk ARI is reachable
curl -u agentvoice:<ASTERISK_ARI_PASSWORD> http://127.0.0.1:8088/ari/asterisk/info

# Verify PJSIP endpoints loaded
curl -u agentvoice:<ASTERISK_ARI_PASSWORD> http://127.0.0.1:8088/ari/endpoints/PJSIP
```
