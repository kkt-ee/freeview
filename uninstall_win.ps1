$ErrorActionPreference = 'Stop'

# Uninstall freeview from dedicated virtual environment and remove env folder.
$VenvName = 'freeviewer'
$VenvDir = Join-Path (Get-Location) $VenvName
$PipExe = Join-Path $VenvDir 'Scripts\pip.exe'

if (!(Test-Path $VenvDir)) {
    Write-Host "Virtual environment '$VenvName' not found. Nothing to remove."
    exit 0
}

if (Test-Path $PipExe) {
    Write-Host "Uninstalling freeview from $VenvName"
    & $PipExe uninstall -y freeview
}

Write-Host "Removing virtual environment directory: $VenvName"
Remove-Item -Recurse -Force $VenvDir

Write-Host "Done. $VenvName has been removed."
