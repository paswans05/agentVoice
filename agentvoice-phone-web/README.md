# agentVoice Phone Web (iPhone 13 Safari Gateway)

Browser-based PWA for connecting an **iPhone 13 (iOS 26 Safari)** to agentVoice over local Wi-Fi HTTPS/WSS without installing a native iOS app.

## Local Development

```powershell
# 1. Run HTTPS setup script from repo root
.\scripts\setup-iphone-https.ps1

# 2. Install & start agentvoice-phone-web (port 3001)
cd agentvoice-phone-web
npm install
npm run dev
```

See [docs/iphone-safari-gateway.md](../docs/iphone-safari-gateway.md) for iOS 26 CA certificate trust and Safari microphone instructions.
