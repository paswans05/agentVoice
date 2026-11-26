# agentVoice — Leads Management, Consent & Suppression (Phase 7)

## 1. Overview

Phase 7 implements local-first Leads Management (`apps/api/app/api/v1/leads.py`, `apps/web/app/leads/*`) backed by `StorageProvider` (`agentvoice-data/leads/`). No outbound calls or automated messages are triggered in Phase 7.

## 2. Roadmap Note (Phase 6)

- **Phases 1–5**: Implemented and verified.
- **Phase 6 (Sales Agent Intelligence)**: Not yet implemented; Phase 7 does not depend on Phase 6 and leaves Phase 6 deferred.
- **Phase 7 (Leads Management)**: Implemented and verified.

## 3. Consent & Suppression Safeguards

1. **Consent Defaults**: Imported and newly created leads always default to `UNKNOWN` consent.
2. **Channel & Purpose Scoping**: Consent is tracked separately per `(lead_id, channel, purpose)` in `leads/consent_records.jsonl`. Granting `EMAIL` consent never grants `PHONE` consent.
3. **Centralized Suppression**: `leads/suppression_store.json` + `leads/suppression_records.jsonl` enforce phone-level and email-level opt-outs. Suppression survives lead deletion, blocks status changes away from `DO_NOT_CONTACT`, and cannot be overwritten by CSV imports.
4. **Eligibility Gate**: `LeadEligibilityService.check_contact_eligibility(lead_id, channel, purpose)` validates both suppression and `GRANTED` consent before any future campaign/telephony action.

## 4. CSV Import & Export

- **Import**: 3-step API (`preview` -> `validate` -> `execute`) with header mapping, duplicate detection (`EMAIL`, `PHONE`, `EMAIL_OR_PHONE` with `SKIP`/`UPDATE_EXISTING`/`IMPORT_AS_NEW`), and Unicode/Hindi support.
- **Export**: UTF-8 with BOM (`utf-8-sig`) for Excel compatibility and formula-injection escaping (`=`, `+`, `-`, `@`, `\t`, `\r` prefixed with `'`).
