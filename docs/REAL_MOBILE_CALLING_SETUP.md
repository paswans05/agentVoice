# Real Indian Mobile Calling Setup Guide (Zero-Budget Dev -> Production)

## 1. Zero-Budget Local Development Mode (Current State)

Without a paid SIP trunk or GSM gateway:
- **Internal Browser & SIP Calling**: Fully functional via `/telephony/dialer` (`1001-ws`, `1002-ws`, Echo `600`, AI `700`).
- **Dry-Run Campaigns**: Test full consent, DNC suppression, calling-window, and AI conversation flows without placing PSTN calls.
- **External PSTN Guard**: Attempting real PSTN calls without an authorized, connected provider/trunk is blocked with `EXTERNAL_TELEPHONY_NOT_CONFIGURED` or `TelephonyPolicyError`.

---

## 2. Moving to Authorized Indian Mobile Calling

1. **Provision a Cloud VPS** with a static public IP (e.g., Mumbai region for low latency to Indian carriers).
2. **Acquire an Authorized Indian SIP Trunk** (e.g., Exotel vSIP, Tata Tele, or Airtel IQ) and complete KYC + TRAI DLT registration.
3. **Configure Asterisk 23 Trunk**: Render [pjsip_trunk.conf.template](file:///d:/open-source/agentVoice/docker/asterisk/pjsip_trunk.conf.template) with your carrier's host, transport, codecs (`ulaw,alaw`), and NAT public IP.
4. **Register Provider & Trunk in AgentVoice UI** (`/telephony/setup` and `/telephony`):
   - Select `SIP Trunk via Asterisk`, choose the matching `SIP Auth Mode` (`ip_whitelist` for Exotel), enter your authorized `caller_id` (`+91...`), and set `allowed_destinations` (`+91*`).
   - Run **Test Connection** on both the Provider and SIP Trunk to verify ARI and `OPTIONS` reachability.
5. **Configure Inbound & Outbound Routes** in `/telephony` and bind your Exophone DID to an `ACTIVE` AI agent.
6. **Launch a Controlled Campaign**: Keep `require_caller_id_authorization`, `block_open_sip_relay`, and `enforce_trai_dlt_compliance` enabled.
