# agentVoice — Campaign Management & Dry-Run Execution (Phase 8)

## 1. Overview

Phase 8 implements outbound campaign management, timezone-aware scheduling (`zoneinfo` + `tzdata`), pre-call consent & suppression enforcement (reusing Phase 7 `LeadEligibilityService`), idempotent local queue/worker execution, retry policies, and real-vs-dry-run analytics.

## 2. Telephony & Compliance Safeguards

- **Dry-Run Mode**: Uses `DryRunTelephonyProvider` to simulate campaign execution locally without placing real phone calls. Every simulated record is flagged `is_dry_run=true` and reported separately from real calls in Analytics.
- **Real Telephony (Phase 9)**: `dry_run=false` with `sip`/`asterisk`/`livekit_sip`/`gsm_gateway` is **blocked (fail-closed)** until an authorized telephony provider is configured in Phase 9.
- **Pre-Call Revalidation**: Immediately before each call attempt, `CampaignEligibilityService` checks phone validity, active agent status, channel/purpose `GRANTED` consent, suppression list, policy, and calling window.

## 3. API Endpoints

- `GET/POST /api/v1/campaigns`, `GET/PUT/DELETE /api/v1/campaigns/{campaign_id}`
- `POST /api/v1/campaigns/{campaign_id}/validate`, `.../activate`, `.../pause`, `.../resume`, `.../stop`, `.../cancel`
- `GET/POST /api/v1/campaigns/{campaign_id}/leads`
- `GET /api/v1/campaigns/{campaign_id}/progress`, `.../jobs`, `.../calls`, `.../events`, `.../analytics`
- `GET /api/v1/campaigns/analytics/overview`, `GET /api/v1/calls`, `GET /api/v1/calls/{call_id}`
- `GET /api/v1/telephony/providers`, `GET /api/v1/telephony/status`, `POST /api/v1/telephony/test-connection`
