"""CSV Import (preview, validate, duplicate detection, execute) and UTF-8 CSV Export."""

from __future__ import annotations

import csv
import io
import uuid

from app.providers.storage import StorageProvider
from app.repositories.lead_repository import LeadActivityRepository, LeadRepository
from app.schemas.leads import (
    ActivityType,
    CSVExportRequest,
    CSVImportPreviewResponse,
    CSVImportResult,
    CSVImportRowError,
    CSVImportValidateRequest,
    ConsentStatus,
    Lead,
    LeadActivity,
    LeadStatus,
)
from app.services.lead_validation import (
    is_valid_email,
    is_valid_phone,
    normalize_phone,
    sanitize_csv_cell,
)
from app.services.suppression_service import SuppressionService

IMPORT_JOBS_DIR = "leads/import_jobs"

SUGGESTED_HEADER_MAP: dict[str, str] = {
    "first_name": "first_name",
    "firstname": "first_name",
    "last_name": "last_name",
    "lastname": "last_name",
    "name": "full_name",
    "full_name": "full_name",
    "fullname": "full_name",
    "email": "email",
    "phone": "phone",
    "mobile": "phone",
    "phone_number": "phone",
    "company": "company",
    "organization": "company",
    "job_title": "job_title",
    "title": "job_title",
    "city": "city",
    "state": "state",
    "country": "country",
    "source": "source",
    "notes": "notes",
}


class LeadImportService:
    """Handles multi-step CSV import with duplicate detection and suppression preservation."""

    def __init__(
        self,
        storage: StorageProvider,
        lead_repo: LeadRepository,
        activity_repo: LeadActivityRepository,
        suppression_svc: SuppressionService,
    ) -> None:
        self._storage = storage
        self._lead_repo = lead_repo
        self._activity = activity_repo
        self._suppression = suppression_svc

    @staticmethod
    def _decode_csv(content: bytes) -> str:
        if not content or not content.strip():
            raise ValueError("CSV file is empty.")
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return content.decode(encoding)
            except UnicodeDecodeError:
                continue
        return content.decode("utf-8", errors="replace")

    async def preview_csv(self, filename: str, content: bytes) -> CSVImportPreviewResponse:
        text = self._decode_csv(content)
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise ValueError("CSV file is missing column headers.")

        headers = [h.strip() for h in reader.fieldnames if h and h.strip()]
        rows: list[dict[str, str]] = []
        for row in reader:
            cleaned_row = {k.strip(): (v or "").strip() for k, v in row.items() if k and k.strip()}
            if any(cleaned_row.values()):
                rows.append(cleaned_row)

        if not rows:
            raise ValueError("CSV file contains headers but no data rows.")

        suggested: dict[str, str] = {}
        for h in headers:
            mapped = SUGGESTED_HEADER_MAP.get(h.lower().replace(" ", "_"))
            if mapped:
                suggested[h] = mapped

        job_id = f"imp_{uuid.uuid4().hex[:10]}"
        self._storage.write_json(
            f"{IMPORT_JOBS_DIR}/{job_id}.json",
            {"job_id": job_id, "filename": filename, "headers": headers, "rows": rows},
        )
        return CSVImportPreviewResponse(
            job_id=job_id,
            filename=filename,
            headers=headers,
            total_rows=len(rows),
            sample_rows=rows[:5],
            suggested_mapping=suggested,
        )

    async def _run_import(
        self, payload: CSVImportValidateRequest, *, dry_run: bool
    ) -> CSVImportResult:
        job = self._storage.read_json(f"{IMPORT_JOBS_DIR}/{payload.job_id}.json", default=None)
        if not job:
            raise LookupError(f"Import job '{payload.job_id}' was not found.")

        rows: list[dict[str, str]] = job["rows"]
        existing_leads = await self._lead_repo.list_all()

        email_index = {l.email.lower(): l for l in existing_leads if l.email}
        phone_index = {l.normalized_phone: l for l in existing_leads if l.normalized_phone}

        imported_count = 0
        skipped_count = 0
        duplicate_count = 0
        invalid_count = 0
        updated_count = 0
        errors: list[CSVImportRowError] = []
        warnings: list[str] = []
        new_leads: list[Lead] = []

        for idx, row in enumerate(rows, start=2):
            mapped: dict[str, str] = {}
            custom: dict[str, str] = {}
            for csv_col, target_field in payload.column_mapping.items():
                val = row.get(csv_col, "").strip()
                if not val or not target_field or target_field == "IGNORE":
                    continue
                if target_field.startswith("custom:"):
                    custom[target_field[7:]] = val
                else:
                    mapped[target_field] = val

            email = mapped.get("email", "").strip().lower() or None
            phone = mapped.get("phone", "").strip() or None
            norm_phone = normalize_phone(phone)

            if not is_valid_email(email):
                invalid_count += 1
                errors.append(CSVImportRowError(row_number=idx, message="Invalid email format."))
                continue
            if not is_valid_phone(phone):
                invalid_count += 1
                errors.append(CSVImportRowError(row_number=idx, message="Invalid phone format."))
                continue

            full_name = (
                mapped.get("full_name")
                or f"{mapped.get('first_name', '')} {mapped.get('last_name', '')}".strip()
            )
            if not full_name and not email and not phone:
                invalid_count += 1
                errors.append(
                    CSVImportRowError(row_number=idx, message="Row has no name, email, or phone.")
                )
                continue

            # Duplicate check (never match on name alone)
            dup_lead: Lead | None = None
            if payload.match_strategy in ("EMAIL", "EMAIL_OR_PHONE") and email:
                dup_lead = email_index.get(email)
            if dup_lead is None and payload.match_strategy in ("PHONE", "EMAIL_OR_PHONE") and norm_phone:
                dup_lead = phone_index.get(norm_phone)

            if dup_lead is not None:
                duplicate_count += 1
                if payload.duplicate_strategy == "SKIP":
                    skipped_count += 1
                    continue
                if payload.duplicate_strategy == "UPDATE_EXISTING":
                    updated_count += 1
                    if not dry_run:
                        # Never overwrite suppression or consent from CSV
                        merged = dup_lead.model_copy(
                            update={
                                "company": mapped.get("company") or dup_lead.company,
                                "job_title": mapped.get("job_title") or dup_lead.job_title,
                                "notes": mapped.get("notes") or dup_lead.notes,
                            }
                        )
                        await self._lead_repo.update(merged)
                    continue

            suppressed = await self._suppression.is_suppressed(phone=phone, email=email)
            if suppressed:
                warnings.append(
                    f"Row {idx}: matches suppression list; imported with DO_NOT_CONTACT status."
                )

            lead_obj = Lead(
                id=f"lead_{uuid.uuid4().hex[:12]}",
                first_name=mapped.get("first_name", ""),
                last_name=mapped.get("last_name", ""),
                full_name=full_name or (email or phone or "Imported Lead"),
                email=email,
                phone=phone,
                normalized_phone=norm_phone,
                company=mapped.get("company", ""),
                job_title=mapped.get("job_title", ""),
                country=mapped.get("country", ""),
                state=mapped.get("state", ""),
                city=mapped.get("city", ""),
                source=mapped.get("source") or "csv_import",
                status=LeadStatus.DO_NOT_CONTACT if suppressed else LeadStatus.NEW,
                notes=mapped.get("notes", ""),
                custom_fields=custom,
                # Imported leads ALWAYS default to UNKNOWN consent
                consent_status=ConsentStatus.UNKNOWN,
                suppressed=suppressed,
            )
            imported_count += 1
            if email:
                email_index[email] = lead_obj
            if norm_phone:
                phone_index[norm_phone] = lead_obj
            new_leads.append(lead_obj)

        if not dry_run and new_leads:
            await self._lead_repo.create_many(new_leads)
            for lead in new_leads:
                await self._activity.append(
                    LeadActivity(
                        activity_id=f"act_{uuid.uuid4().hex[:12]}",
                        lead_id=lead.id,
                        activity_type=ActivityType.CSV_IMPORTED,
                        description=f"Imported from CSV ({job['filename']})",
                    )
                )

        result = CSVImportResult(
            job_id=payload.job_id,
            total_rows=len(rows),
            imported_count=imported_count,
            skipped_count=skipped_count,
            duplicate_count=duplicate_count,
            invalid_count=invalid_count,
            updated_count=updated_count,
            errors=errors,
            warnings=warnings,
        )
        if not dry_run:
            self._storage.write_json(
                f"{IMPORT_JOBS_DIR}/{payload.job_id}_result.json",
                result.model_dump(mode="json"),
            )
        return result

    async def validate_import(self, payload: CSVImportValidateRequest) -> CSVImportResult:
        return await self._run_import(payload, dry_run=True)

    async def execute_import(self, payload: CSVImportValidateRequest) -> CSVImportResult:
        return await self._run_import(payload, dry_run=False)


class LeadExportService:
    """Exports filtered or selected leads to UTF-8 BOM CSV with formula-injection escaping."""

    def __init__(self, lead_repo: LeadRepository) -> None:
        self._lead_repo = lead_repo

    async def export_csv(self, payload: CSVExportRequest) -> bytes:
        leads = await self._lead_repo.list_all()
        if payload.lead_ids:
            id_set = set(payload.lead_ids)
            leads = [l for l in leads if l.id in id_set]
        if payload.status is not None:
            leads = [l for l in leads if l.status == payload.status]
        if payload.assigned_agent_id is not None:
            leads = [l for l in leads if l.assigned_agent_id == payload.assigned_agent_id]
        if payload.group_id is not None:
            leads = [l for l in leads if payload.group_id in l.group_ids]

        columns = [
            "id",
            "full_name",
            "email",
            "phone",
            "company",
            "job_title",
            "status",
            "priority",
            "source",
            "suppressed",
            "created_at",
        ]
        if payload.include_consent:
            columns.append("consent_status")

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(columns)

        for lead in leads:
            row = [
                sanitize_csv_cell(lead.id),
                sanitize_csv_cell(lead.full_name),
                sanitize_csv_cell(lead.email or ""),
                sanitize_csv_cell(lead.phone or ""),
                sanitize_csv_cell(lead.company),
                sanitize_csv_cell(lead.job_title),
                sanitize_csv_cell(lead.status.value),
                sanitize_csv_cell(lead.priority.value),
                sanitize_csv_cell(lead.source),
                sanitize_csv_cell(lead.suppressed),
                sanitize_csv_cell(lead.created_at.isoformat()),
            ]
            if payload.include_consent:
                row.append(sanitize_csv_cell(lead.consent_status.value))
            writer.writerow(row)

        # UTF-8 with BOM so Hindi/Unicode renders cleanly in Excel
        return buf.getvalue().encode("utf-8-sig")
