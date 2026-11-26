# Pledge Reminders: office use

## Use the app

1. Open `PledgeReminders.exe` on a Windows computer.
2. Click **Browse** beside **Donor CSV** and select the current export. The app shows the donor count and signature image filenames. The reminder template is included in the app. A signature image named in the CSV can sit beside the CSV; otherwise the included `alan_kelly_sig.png` is used when that is the named image.
3. Click **Browse** beside **Save results in** and choose a folder you can write to.
4. Click **Generate**. The app creates a new folder named with the date, time, and donor count. It contains one PDF per donor and `Merged_Pledge_Reminders_Batch_Signed.pdf` for the full print batch. A second run creates another folder.

## Check on a coworker's computer

1. Copy only `dist\PledgeReminders.exe` to another Windows computer. The coworker does not need Python or VS Code.
2. Open it and use the sample CSV in `INPUT_CSV` (share that sample separately for the test). Choose a test output folder.
3. Confirm the app lists 30 donors and `alan_kelly_sig.png`, then generate. Confirm there are 30 individual PDFs and one 60-page merged PDF. Open a few letters and check names, amounts, and signature. Run it again and confirm it makes a different output folder.
4. If Windows or office security software blocks the app, have your IT team review and approve the executable before office distribution.

## Share with the office

After the coworker test and IT approval, put the executable in an office SharePoint or OneDrive folder shared with the staff who need it. Keep real donor CSVs and generated letters in your office's approved restricted location. Share the app link and these instructions; coworkers should open or copy the approved executable. When the app changes, replace the shared executable with the newly tested version.

## Rebuild from source

On a Windows development computer, install the dependencies in `.venv`, including `pypdf`, `reportlab`, and `pyinstaller`, then run `build_windows.ps1`. The executable is written to `dist\PledgeReminders.exe`. The template and default signature are bundled into the executable.
