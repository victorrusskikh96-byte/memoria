# Memoria development environment on Windows

Status: baseline for the first implementation phase.

## Recommended host

Use Windows 11 with WSL 2 and Docker Desktop. Windows 10 support ended on
14 October 2025. If an immediate upgrade is impossible, use Windows 10 22H2
build 19045 with Microsoft Consumer ESU only as a temporary bridge, then plan
the move to Windows 11.

Minimum practical workstation:

- 64-bit CPU with hardware virtualization enabled;
- 16 GB RAM recommended (8 GB is the Docker minimum);
- 20 GB free SSD space for tools, images, and database data;
- BitLocker/device encryption, Microsoft Defender, and firewall enabled.

## 1. Audit before changing anything

Open PowerShell in the repository and run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\check-environment.ps1 -OutputPath .\environment-report.txt
```

The report contains tool versions and capability flags only. It intentionally
does not collect usernames, serial numbers, IP addresses, or secrets.

## 2. Install the user-level tools

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\install-user-tools.ps1
uv python install 3.13
```

Close and reopen PowerShell after installation. Do not install Python from the
Microsoft Store for this project; uv manages the pinned interpreter.

## 3. Enable WSL 2

Run an elevated PowerShell window:

```powershell
wsl --install
```

Restart if Windows asks. Then verify:

```powershell
wsl --status
wsl --update
```

Use WSL 2 as Docker's Linux backend. Application commands may remain in normal
PowerShell; no GNU `make` dependency is required.

## 4. Install Docker Desktop

Install Docker Desktop from Docker's official installer, choose the WSL 2
backend, and verify:

```powershell
docker version
docker compose version
```

The development database is published only to `127.0.0.1`; it is not exposed
to the local network.

## 5. Put the repository in a stable local path

Recommended path:

```text
C:\Users\<you>\PycharmProjects\memoria
```

Avoid OneDrive-synchronised folders for source code, `.venv`, and PostgreSQL
volumes. Cloud sync can create lock, permission, and line-ending conflicts.

## 6. Bootstrap Memoria

From the repository root:

```powershell
Copy-Item .env.example .env
.\scripts\dev.ps1 sync
.\scripts\dev.ps1 up
.\scripts\dev.ps1 migrate
.\scripts\dev.ps1 check
.\scripts\dev.ps1 run
```

Open <http://127.0.0.1:8000/docs> and
<http://127.0.0.1:8000/health/ready>.

Stop services with:

```powershell
.\scripts\dev.ps1 down
```

## 7. Configure PyCharm

1. Open the `memoria` directory as the project.
2. Select the existing interpreter at `.venv\Scripts\python.exe`.
3. Mark `src` as Sources Root if PyCharm does not infer it.
4. Set Ruff as the formatter, or run `.\scripts\dev.ps1 format`.
5. Create a Python run configuration for `uvicorn` with parameters
   `memoria.main:app --reload` and working directory set to the repository root.

## Security rules for development

- Never use real family documents, recordings, biometric material, or legal
  evidence in local development; use synthetic fixtures.
- Never commit `.env`, credentials, database dumps, or environment reports.
- Keep MFA enabled on Git hosting and package registries.
- Do not forward PostgreSQL or the API through a public tunnel without a
  separate threat review.
- Treat deletion, export, consent, and succession flows as privileged actions
  even in prototypes.

## Troubleshooting

If PowerShell blocks a script, use `Set-ExecutionPolicy -Scope Process Bypass`;
this affects only the current window. If port 5432 is occupied, stop the other
local PostgreSQL service or change both the Compose port and `.env` URL. If
Docker reports that virtualization is unavailable, enable Intel VT-x or AMD-V
in BIOS/UEFI and re-run the audit.
