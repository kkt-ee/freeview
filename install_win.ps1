$ErrorActionPreference = 'Stop'

# Minimal installer for a dedicated freeviewer virtual environment on Windows.
$VenvName = 'freeviewer'
$VenvDir = Join-Path (Get-Location) $VenvName
$PackageSpec = if ($args.Count -gt 0) { $args[0] } else { 'freeview' }

$UsePyLauncher = $false
if (Get-Command py -ErrorAction SilentlyContinue) {
    $UsePyLauncher = $true
} elseif (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error 'Python 3 was not found. Install Python first.'
}

Write-Host "Creating virtual environment: $VenvDir"
if ($UsePyLauncher) {
    & py -3 -m venv $VenvDir
} else {
    & python -m venv $VenvDir
}

$PythonExe = Join-Path $VenvDir 'Scripts\python.exe'
$PipExe = Join-Path $VenvDir 'Scripts\pip.exe'
$FreeviewExe = Join-Path $VenvDir 'Scripts\freeview.exe'

if (!(Test-Path $PythonExe) -or !(Test-Path $PipExe)) {
    Write-Error 'Virtual environment creation failed.'
}

Write-Host "Upgrading pip in $VenvName"
& $PythonExe -m pip install --upgrade pip

Write-Host "Installing package: $PackageSpec"
& $PipExe install $PackageSpec

Write-Host ''
Write-Host "Installed successfully in .\$VenvName"
Write-Host 'Run the app with:'
Write-Host "  .\$VenvName\Scripts\freeview.exe serve"
Write-Host 'Optional cert setup:'
Write-Host "  .\$VenvName\Scripts\freeview.exe cert"
