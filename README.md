# Generate Pledge Reminders

A Windows desktop app that turns a donor CSV into individual two-page pledge reminder PDFs and one merged print batch.

## Run locally

Install Python 3.14, then:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe pledge_reminders_app.py
```

The app needs `docs/Pledge Reminder Blank Template.pdf` and the signature image named in the CSV (for example `docs/alan_kelly_sig.png`). These office assets and donor data are intentionally excluded from this public repository.

## Build the Windows app

After placing the approved template and signature image in `docs`, install PyInstaller and run:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\build_windows.ps1
```

The build creates `dist/PledgeReminders.exe`. See [OFFICE_USE.md](OFFICE_USE.md) for coworker testing and sharing instructions.
