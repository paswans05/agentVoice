# Exotel SIP Trunk Integration Readiness (India)

## 1. Technical Requirements (Verified against Exotel vSIP Architecture)

| Requirement | Exotel vSIP Specification | AgentVoice Readiness |
|---|---|---|
| **Authentication Mode** | **IP Authentication / Whitelisting** (no `SIP REGISTER` required) | **READY** (`SipAuthMode.IP_WHITELIST` + `[sip-trunk-external-identify]` in PJSIP) |
| **Signaling Transport & Ports** | **TCP Port 5070** (`pstn.in2.exotel.com` / `pstn.in4.exotel.com`) or **TLS Port 443** (`<accountsid>.pstn.exotel.com`) | **READY** (`TransportProtocol.TCP` / `TLS` + `pjsip_trunk.conf.template`) |
| **Media (RTP / SRTP)** | **UDP 10000–40000** (SRTP when using TLS) | **PARTIAL** (Local Docker maps `10000-10018` due to Windows port bindings; VPS deployment should open `10000-40000/udp`) |
| **Codecs** | G.711 `alaw` (`PCMA`) and `ulaw` (`PCMU`) | **READY** (`TelephonyMediaAdapter` + `pjsip_trunk.conf.template`) |
| **Caller ID / DID** | Exophone (Virtual Number) mapped via Exotel Flow (*Connect Applet*) | **BLOCKED BY PROVIDER** (Requires active Exotel account & KYC-verified Exophone) |
| **Static Public IP** | Required for Exotel ACL whitelisting | **BLOCKED BY ENVIRONMENT** (Local Windows PC is behind residential NAT; requires Cloud VPS) |

---

## 2. Regulatory & Account Prerequisites (India)

1. **KYC & Business Verification**: Exotel requires business KYC before activating PSTN outbound/inbound virtual numbers (Exophones).
2. **TRAI DLT Registration**: Commercial/promotional/transactional outbound calling in India requires DLT entity & template compliance (`TelephonySettings.enforce_trai_dlt_compliance = true`).
3. **Exotel ACL Whitelisting**: Your Asterisk server's static public IP must be added to Exotel's IP ACL.

---

## 3. Open Questions Before Provisioning

1. Will you deploy Asterisk on a cloud VPS (e.g., AWS Mumbai / DigitalOcean Bangalore) with a static public IP?
2. Which Exotel edge PoP (`pstn.in2.exotel.com` vs `pstn.in4.exotel.com`) and transport (TCP 5070 vs TLS 443) is assigned to your Exotel account?
3. What is your KYC-approved Exophone DID (`+91...`) for `caller_id` and `InboundRoute` matching?

---

## 4. Current Status

- **Software & Config**: Ready (`ip_whitelist` auth mode, PJSIP template, caller ID & DNC guards).
- **Live PSTN Calling**: **BLOCKED BY PROVIDER** (No Exotel account, no static public IP, zero-budget local mode active).
