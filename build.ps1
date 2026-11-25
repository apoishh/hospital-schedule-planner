# Builds "HO Roster.exe" and packs release\HO Roster.zip
$ErrorActionPreference = "Stop"
$py = "$env:USERPROFILE\.venvs\hospital-roster\Scripts\python.exe"
$b = "$env:USERPROFILE\.venvs\hospital-roster-build"
if (-not (Test-Path $py)) {
    python -m venv "$env:USERPROFILE\.venvs\hospital-roster"
    & $py -m pip install -r "$PSScriptRoot\requirements.txt" pyinstaller
}
# PyInstaller logs to stderr; don't let PowerShell 5.1 treat that as a failure
$ErrorActionPreference = "Continue"
& $py -m PyInstaller --noconfirm --windowed --onedir --name "HO Roster" --collect-all ortools `
    --exclude-module matplotlib --exclude-module IPython `
    --add-data "$PSScriptRoot\roster\viewer_template.html;roster" `
    --collect-data sv_ttk `
    --distpath "$b\dist" --workpath "$b\work" --specpath $b "$PSScriptRoot\app.py" 2>&1 | Out-File "$b\pyinstaller.log"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed - see $b\pyinstaller.log" }
$ErrorActionPreference = "Stop"
Copy-Item "$PSScriptRoot\release-files\How to use HO Roster.txt" "$b\dist\HO Roster\" -Force
Copy-Item "$PSScriptRoot\RULES CHECKLIST.md" "$b\dist\HO Roster\" -Force
Copy-Item "$PSScriptRoot\examples\Roster Data EXAMPLE.xlsx" "$b\dist\HO Roster\" -Force
New-Item -ItemType Directory -Force "$PSScriptRoot\release" | Out-Null
Compress-Archive -Path "$b\dist\HO Roster" -DestinationPath "$PSScriptRoot\release\HO Roster.zip" -Force
Write-Host "Built: $PSScriptRoot\release\HO Roster.zip"
