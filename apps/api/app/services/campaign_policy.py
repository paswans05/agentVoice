"""Timezone-aware CampaignScheduler, Policy checks, and Retry backoff calculator."""

from __future__ import annotations

from datetime import date, datetime, time as dt_time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.schemas.campaigns import CallOutcome, Campaign


class CampaignScheduler:
    """Validates and evaluates timezone-aware campaign calling windows."""

    @staticmethod
    def validate_schedule(campaign: Campaign) -> list[str]:
        errors: list[str] = []
        try:
            ZoneInfo(campaign.timezone)
        except ZoneInfoNotFoundError:
            errors.append(f"Invalid timezone '{campaign.timezone}'.")

        if not campaign.calling_days or any(d < 0 or d > 6 for d in campaign.calling_days):
            errors.append("calling_days must contain weekday integers between 0 (Mon) and 6 (Sun).")

        sh, sm = map(int, campaign.start_time.split(":"))
        eh, em = map(int, campaign.end_time.split(":"))
        if not (0 <= sh <= 23 and 0 <= sm <= 59 and 0 <= eh <= 23 and 0 <= em <= 59):
            errors.append("start_time and end_time must be valid HH:MM values.")
        elif (sh, sm) >= (eh, em):
            errors.append("start_time must be earlier than end_time.")

        if campaign.start_date and campaign.end_date:
            try:
                sd = date.fromisoformat(campaign.start_date)
                ed = date.fromisoformat(campaign.end_date)
                if sd > ed:
                    errors.append("start_date cannot be after end_date.")
            except ValueError:
                errors.append("start_date and end_date must use YYYY-MM-DD format.")
        return errors

    @staticmethod
    def is_within_calling_window(campaign: Campaign, now_utc: datetime | None = None) -> tuple[bool, str]:
        try:
            tz = ZoneInfo(campaign.timezone)
        except ZoneInfoNotFoundError:
            return False, f"Invalid timezone '{campaign.timezone}'."

        current_utc = now_utc or datetime.now(timezone.utc)
        local_dt = current_utc.astimezone(tz)
        local_date = local_dt.date()

        if campaign.start_date:
            if local_date < date.fromisoformat(campaign.start_date):
                return False, f"Campaign starts on {campaign.start_date}."
        if campaign.end_date:
            if local_date > date.fromisoformat(campaign.end_date):
                return False, f"Campaign ended on {campaign.end_date}."

        if local_dt.weekday() not in campaign.calling_days:
            return False, "Current weekday is outside permitted calling_days."

        sh, sm = map(int, campaign.start_time.split(":"))
        eh, em = map(int, campaign.end_time.split(":"))
        start_t = dt_time(sh, sm)
        end_t = dt_time(eh, em)
        if not (start_t <= local_dt.time() <= end_t):
            return False, (
                f"Current local time ({local_dt.strftime('%H:%M')} {campaign.timezone}) "
                f"is outside calling window {campaign.start_time}-{campaign.end_time}."
            )
        return True, "Within permitted calling window."


class CampaignPolicyService:
    """Enforces fail-closed compliance and provider authorization policies."""

    @staticmethod
    def check_policy(campaign: Campaign) -> tuple[bool, str]:
        if not campaign.dry_run and campaign.telephony_provider.strip().lower() == "dry_run":
            return False, "Non-dry-run campaign cannot use the dry_run provider."
        if not campaign.dry_run:
            # Real telephony requires Phase 9 authorized provider configuration
            return (
                False,
                f"Real outbound calling via '{campaign.telephony_provider}' is blocked until "
                "an authorized telephony provider is configured (Phase 9).",
            )
        return True, "Dry-run policy check passed."


NON_RETRYABLE_OUTCOMES = {
    CallOutcome.INTERESTED,
    CallOutcome.NOT_INTERESTED,
    CallOutcome.CALLBACK_REQUESTED,
    CallOutcome.APPOINTMENT_BOOKED,
    CallOutcome.NEEDS_HUMAN,
    CallOutcome.INFORMATION_REQUESTED,
    CallOutcome.WRONG_NUMBER,
    CallOutcome.DO_NOT_CALL,
}


class CampaignRetryService:
    """Determines whether a failed/unanswered attempt may be retried and computes backoff."""

    @staticmethod
    def should_retry(campaign: Campaign, outcome: CallOutcome, attempt_number: int) -> bool:
        if outcome in NON_RETRYABLE_OUTCOMES:
            return False
        if attempt_number >= campaign.maximum_attempts_per_lead:
            return False
        if outcome == CallOutcome.NO_ANSWER:
            return campaign.retry_policy.retry_on_no_answer
        if outcome == CallOutcome.BUSY:
            return campaign.retry_policy.retry_on_busy
        if outcome == CallOutcome.FAILED:
            return campaign.retry_policy.retry_on_provider_error
        return False

    @staticmethod
    def next_retry_time(
        campaign: Campaign, attempt_number: int, now_utc: datetime | None = None
    ) -> datetime:
        base = now_utc or datetime.now(timezone.utc)
        exponent = max(0, attempt_number - 1)
        delay_minutes = int(
            campaign.retry_interval_minutes * (campaign.retry_policy.backoff_multiplier ** exponent)
        )
        delay_minutes = max(
            campaign.minimum_interval_between_attempts_minutes,
            min(delay_minutes, campaign.retry_policy.max_retry_delay_minutes),
        )
        return base + timedelta(minutes=delay_minutes)
