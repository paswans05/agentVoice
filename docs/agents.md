# agentVoice — Agent Management (Phase 2)

## 1. Agent Schema

Each agent is stored as a validated JSON document in `agentvoice-data/agents/{agent_id}.json` via `StorageProvider`.

### Core Fields

- `id`: Unique string identifier (`agent_<12-hex>`)
- `name`: 2–80 characters
- `description`: Up to 500 characters
- `avatar`: Icon identifier (`bot`, `briefcase`, `headphones`, `target`, `calendar`, `sparkles`)
- `type`: `SALES | CUSTOMER_SUPPORT | LEAD_QUALIFICATION | APPOINTMENT_BOOKING | GENERAL_ASSISTANT | CUSTOM`
- `status`: `DRAFT | ACTIVE | INACTIVE`
- `personality`: `tone` (`FRIENDLY`, `PROFESSIONAL`, `FORMAL`, `CASUAL`, `CONFIDENT`, `EMPATHETIC`, `CUSTOM`), `traits`, `custom_instructions`
- `instructions`: `system_prompt`, `greeting`, `additional_rules` (stored as configuration, never executed)
- `language`: `primary_language` (`hi-IN`, `en-IN`), `supported_languages`, `hinglish_enabled` (boolean behavior flag), `response_mode` (`AUTO`, `PRIMARY`, `FIXED`)
- `voice`: `provider`, `voice_id`, `speed` (`0.5`–`2.0`), `pitch` (`0.5`–`2.0`) — preferences can be saved without an installed TTS engine
- `created_at`, `updated_at`, `version`

## 2. Lifecycle Rules

1. New agents always start in `DRAFT`.
2. Activating an agent validates required fields (including a non-empty `system_prompt`, `primary_language`, and `voice` preferences) and transitions `DRAFT`/`INACTIVE` → `ACTIVE`.
3. `ACTIVE` agents can be deactivated to `INACTIVE`.
4. `DRAFT` agents cannot be deactivated directly (edit or delete instead).
5. Duplicating an agent creates a new `DRAFT` agent with a fresh `id`, `" (Copy)"` suffix, `version = 1`, and reset timestamps.

## 3. API Endpoints

All endpoints return the standard `ApiResponse<T>` envelope:

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/agents/templates` | List built-in starter templates |
| `GET` | `/api/v1/agents` | List agents (`?search=`, `?status=`, `?type=`) |
| `POST` | `/api/v1/agents` | Create a new agent (`DRAFT`) |
| `GET` | `/api/v1/agents/{agent_id}` | Get agent by ID |
| `PUT` | `/api/v1/agents/{agent_id}` | Update agent configuration |
| `DELETE` | `/api/v1/agents/{agent_id}` | Delete agent |
| `POST` | `/api/v1/agents/{agent_id}/duplicate` | Duplicate agent as `DRAFT` |
| `POST` | `/api/v1/agents/{agent_id}/activate` | Validate and activate agent |
| `POST` | `/api/v1/agents/{agent_id}/deactivate` | Deactivate `ACTIVE` agent |

## 4. Starter Templates

Built-in editable templates in `apps/api/app/agents/templates.py`:
- Sales Assistant (`sales-assistant`)
- Customer Support Assistant (`customer-support`)
- Lead Qualification Assistant (`lead-qualification`)
- Appointment Booking Assistant (`appointment-booking`)
- General Assistant (`general-assistant`)
