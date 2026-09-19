[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet("sync", "up", "down", "migrate", "test", "integration", "lint", "format", "run", "check")]
    [string]$Task = "check"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found. See docs/07-engineering/DEVELOPMENT_ENVIRONMENT_WINDOWS.md"
    }
}

Require-Command "uv"

switch ($Task) {
    "sync" { uv sync --all-groups }
    "up" {
        Require-Command "docker"
        docker compose up -d --wait
    }
    "down" {
        Require-Command "docker"
        docker compose down
    }
    "migrate" { uv run alembic upgrade head }
    "test" { uv run pytest }
    "integration" {
        $env:MEMORIA_RUN_INTEGRATION_TESTS = "1"
        try {
            uv run alembic upgrade head
            uv run pytest tests/integration
        } finally {
            Remove-Item Env:MEMORIA_RUN_INTEGRATION_TESTS -ErrorAction SilentlyContinue
        }
    }
    "lint" {
        uv run ruff check .
        uv run mypy
    }
    "format" { uv run ruff format . }
    "run" { uv run uvicorn memoria.main:app --reload }
    "check" {
        uv run ruff check .
        uv run ruff format --check .
        uv run mypy
        uv run pytest
    }
}
