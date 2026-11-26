$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $project

& ".\.venv\Scripts\python.exe" -m PyInstaller `
    --clean --noconfirm --onefile --windowed `
    --name PledgeReminders `
    --add-data "docs\Pledge Reminder Blank Template.pdf;docs" `
    --add-data "docs\alan_kelly_sig.png;docs" `
    pledge_reminders_app.py

if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed" }
Write-Host "Built dist\PledgeReminders.exe"
