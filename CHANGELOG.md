# EmployeeMint Changelog

All notable changes made during development sessions are recorded here with **date/time (IST)**, **what changed**, **why**, and **expected impact**.

---

## How to use this file (going forward)

When making any fix or feature, append a new entry under `[Unreleased]` using this template:

```markdown
### YYYY-MM-DD HH:MM IST — Short title

| | |
|---|---|
| **Type** | Feature / Fix / Enhancement / Infra / Security |
| **Area** | e.g. Payroll, Recruitment, Database |
| **Why** | Root cause or business reason |
| **Impact** | What users/devs will notice; migration/restart needed? |
| **Files** | Key paths changed |

- Bullet details of what changed
```

After a release, move `[Unreleased]` entries under a dated version heading.

---

## [Unreleased]

### 2026-08-22 12:31 IST — Database connection pool & transaction leak fix

| | |
|---|---|
| **Type** | Fix (production-critical) |
| **Area** | Database / Backend infra |
| **Why** | PostgreSQL logged `unexpected EOF on client connection with an open transaction`. Client disconnects (browser refresh, timeout, uvicorn reload) left DB sessions open. Connection pool exhausted → API hung with no error and no new queries. |
| **Impact** | Requests no longer hang indefinitely; stuck transactions auto-cleaned. **Restart required:** Postgres container + backend after deploy. One-time cleanup SQL may be needed for existing stuck connections. |
| **Files** | `backend/app/core/database.py`, `backend/app/core/config.py`, `backend/app/main.py`, `docker-compose.yml`, `.env.example` |

- `get_db()` now rolls back open transactions in `finally` and on `BaseException` (includes `CancelledError` on client disconnect).
- Engine: `pool_reset_on_return="rollback"`, `pool_timeout=30s`, asyncpg `command_timeout=60s`.
- Configurable pool settings: `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE`, `DB_COMMAND_TIMEOUT`.
- Postgres Docker: `idle_in_transaction_session_timeout=60s`, `statement_timeout=5min`, `lock_timeout=30s`.
- `/health` endpoint now reports database connectivity (`database: ok | unreachable`).
- Engine disposed cleanly on app shutdown.

---

### 2026-08-13 18:35 IST — Resume parse 400 error fix

| | |
|---|---|
| **Type** | Fix |
| **Area** | Recruitment |
| **Why** | `POST /api/v1/candidates/parse-resume` returned 400 for common uploads: legacy `.doc`, scanned PDFs, missing `python-docx`, empty files. Frontend showed generic error. |
| **Impact** | Users see clear error messages (e.g. “Use DOCX not DOC”, “scanned PDF not supported”). DOCX parsing works after `pip install -r requirements.txt`. |
| **Files** | `backend/app/services/resume_extract_service.py` (new), `backend/app/services/candidate_service.py`, `backend/app/api/v1/recruitment.py`, `backend/app/services/policy_file_extract.py`, `backend/requirements.txt`, `frontend/src/features/recruitment/CandidatesPage.tsx` |

- Added dedicated resume extraction with extension validation and friendly errors.
- Added `python-docx==1.1.2` dependency.
- Improved PDF error handling (empty/corrupt/password-protected).
- Frontend parses and displays actual API error message from response body.

---

### 2026-08-13 18:42 IST — Recruitment module (HR Lifecycle)

| | |
|---|---|
| **Type** | Feature |
| **Area** | Recruitment / HR Lifecycle |
| **Why** | No candidate tracking existed; offer letters used free-text fields with no hire workflow. Needed: candidates, resume upload, status pipeline, offer link, accept → employee + My Pay. |
| **Impact** | HR can manage full hire pipeline under **HR Lifecycle → Recruitment**. Accept offer creates employee, links offer, syncs compensation, starts onboarding. **Migration required:** `alembic upgrade head` (013). **Seed + re-login** for new permissions. |
| **Files** | `backend/app/models/recruitment.py`, `backend/alembic/versions/013_candidates_recruitment.py`, `backend/app/api/v1/recruitment.py`, `backend/app/services/candidate_service.py`, `backend/app/services/resume_parse_service.py`, `backend/app/schemas/candidate.py`, `frontend/src/features/recruitment/*`, `HRLifecyclePage.tsx`, `AppLayout.tsx`, `App.tsx`, `permissions_seed.py`, `misc.py` (OfferLetter FKs) |

- **Candidate model:** profile, resume, status pipeline, link to employee.
- **OfferLetter extended:** `candidate_id`, `employee_id`, `accepted_at`.
- **API:** CRUD, resume upload/parse, create offer for candidate, accept offer → hire.
- **Accept offer flow:** creates User + Employee, assigns Employee role, syncs `EmployeeCompensation` from offer, optional onboarding start.
- **Permissions:** `recruitment.view`, `recruitment.manage` (HR Admin / HR Executive).
- **Frontend:** Candidates list, detail page with status, offers, accept & hire modal.

---

### 2026-08-13 18:08 IST — Payroll Runs UI visibility fix

| | |
|---|---|
| **Type** | Fix |
| **Area** | Payroll / Permissions |
| **Why** | “New Draft” button and “Payroll Runs” nav were hidden because new payroll permissions were not backfilled on existing tenants, and UI gated too strictly on `payroll.draft` only. |
| **Impact** | HR/Finance users see Payroll Runs in sidebar and prominent **New Draft** button after seed + re-login. Empty state auto-opens create modal. |
| **Files** | `frontend/src/features/payroll/PayrollRunsPage.tsx`, `AppLayout.tsx`, `FinancePage.tsx`, `backend/app/services/rbac_service.py`, `backend/app/scripts/seed.py`, `backend/app/api/v1/payroll.py` |

- Added `sync_system_role_permissions()` to backfill missing permissions on system roles for all tenants.
- Broadened nav visibility to include `payroll.process`, `payroll.submit`, etc.
- Moved **New Draft** to page header; added workflow guide and permission-denied banner.
- `payroll.process` can also create/edit drafts (Finance Admin legacy permission).

---

### 2026-08-13 17:52 IST — Payroll Run workflow (monthly payroll)

| | |
|---|---|
| **Type** | Feature |
| **Area** | Payroll / Finance |
| **Why** | No monthly payroll lifecycle existed — only compensation config and payslip read API. Needed HR draft → Finance approve → bank Excel → payment upload → payslip generation. |
| **Impact** | Full monthly payroll at **Payroll Runs** (`/app/payroll`). Employees add bank details in My Pay; payslips with PDF download after finalize. **Migration required:** `alembic upgrade head` (012). **Dependency:** `openpyxl`. |
| **Files** | `backend/app/models/finance.py`, `backend/alembic/versions/012_payroll_runs.py`, `backend/app/services/payroll_service.py`, `backend/app/api/v1/payroll.py`, `backend/app/schemas/payroll.py`, `frontend/src/features/payroll/PayrollRunsPage.tsx`, `SettingsPage.tsx` (Payroll tab), `permissions_seed.py`, `requirements.txt` |

- **Models:** `PayrollRun`, `PayrollRunLine`, `EmployeeBankAccount`.
- **Workflow:** draft → submitted → approved/rejected → processing → completed.
- **HR:** auto-populate active employees, LOP from unpaid leave, edit bonus/adjustments.
- **Finance:** approve/reject, export bank Excel, upload payment status, finalize + generate payslip PDFs.
- **Permissions:** `payroll.draft`, `payroll.submit`, `payroll.approve`, `payroll.export`, `payroll.import`, `payroll.finalize`.
- **Settings:** Payroll tab for working days and role groups.

---

## Deployment checklist (cumulative unreleased)

| Step | Command / action |
|------|------------------|
| Install deps | `cd backend && pip install -r requirements.txt` |
| Run migrations | `cd backend && alembic upgrade head` |
| Seed permissions | `cd backend && python -m app.scripts.seed` |
| Restart Postgres | `docker compose up -d postgres` (applies timeout settings) |
| Restart backend | Restart uvicorn / backend service |
| Re-login | All users refresh JWT for new permissions |
| Health check | `curl http://localhost:8000/health` |

---

## Version history

| Version | Date | Notes |
|---------|------|-------|
| Unreleased | 2026-08-13 – 2026-08-22 | Payroll runs, recruitment, DB pool fix (see above) |
