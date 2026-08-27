# Catalyst Data Store bulk import for the Saksha migration kit.
#
# Imports every seeded CSV (data/*.csv with rows) into the Catalyst project
# currently selected via `catalyst project`. Run this AFTER creating the 32
# tables + columns manually in the Catalyst console (see TABLE_SPECS.md).
#
# Usage:
#   .\import_all.ps1                    # imports into the dev project
#   .\import_all.ps1 -Production        # imports into the production project
#
# CLI reference:
#   https://docs.catalyst.zoho.com/en/cli/v1/data-store-import-and-export/import-operation/
[CmdletBinding()]
param(
    [switch]$Production
)

$ErrorActionPreference = "Stop"
$DataDir = Join-Path $PSScriptRoot "data"

# Tables in the order they must be imported so parent rows exist first.
# 13 seeded tables (99 demo rows); the other 19 tables are created with 0 rows.
$Order = @(
    "roles", "users", "officers", "locations", "crime_categories",
    "crime_cases", "criminals", "victims", "firs",
    "fir_criminal_links", "fir_victim_links", "evidence", "notifications"
)

if (-not (Get-Command catalyst -ErrorAction SilentlyContinue)) {
    throw "The Catalyst CLI is not on PATH. Install it first: https://docs.catalyst.zoho.com/en/cli/introduction/"
}

$prodFlag = @()
if ($Production) { $prodFlag = @("--production") }

$imported = 0
foreach ($table in $Order) {
    $csv = Join-Path $DataDir "$table.csv"
    if (-not (Test-Path -LiteralPath $csv)) {
        Write-Warning "Missing $csv - skipping"
        continue
    }
    $lines = (Get-Content -LiteralPath $csv).Count
    $rows = [Math]::Max(0, $lines - 1)   # minus the header line
    if ($rows -eq 0) {
        Write-Host "  SKIP  $table (0 rows)"
        continue
    }
    Write-Host "  IMPORT $table ($rows rows) -> $csv"
    & catalyst ds:import $csv --table $table @prodFlag
    if ($LASTEXITCODE -ne 0) {
        throw "Import failed for $table (exit $LASTEXITCODE)."
    }
    $imported += $rows
}

Write-Host ""
Write-Host "Done. $imported rows imported."
Write-Host "Check job status with: catalyst ds:status"
Write-Host "Verify data with: python verify_catalyst.py --catalyst (or run the ZCQL checks in VERIFICATION.md)."