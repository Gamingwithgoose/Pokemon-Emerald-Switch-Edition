param([switch]$PrepareFolders)
$ErrorActionPreference = 'Stop'
try {
    Set-Location -LiteralPath $PSScriptRoot
    foreach ($folder in @('switch files/exefs','switch files/control 0','Emerald rom','Homescreen Icon','Release')) {
        New-Item -ItemType Directory -Path (Join-Path $PSScriptRoot $folder) -Force | Out-Null
    }
    if ($PrepareFolders) { Write-Host 'Input folders are ready. Follow README.md to add your files.'; exit 0 }
    if (-not (Test-Path -LiteralPath '.venv/Scripts/python.exe')) {
        Write-Host 'Setting up the local Python environment...'
        if (Get-Command py -ErrorAction SilentlyContinue) {
            & py -3.14 -m venv .venv
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            & python -c "import sys; assert sys.version_info[:2] == (3,14), 'Install Python 3.14 (64-bit) first.'"
            if ($LASTEXITCODE -ne 0) { throw 'Python 3.14 is required. See Required Software.txt.' }
            & python -m venv .venv
        } else { throw 'Python was not found. Install Python 3.14 (64-bit), then run this again.' }
        if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python environment. See Required Software.txt.' }
    }
    $python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    $requirementsHash = (& $python -c "import hashlib,pathlib; print(hashlib.sha256(pathlib.Path('builder/requirements.txt').read_bytes()).hexdigest())").Trim()
    if ($LASTEXITCODE -ne 0) { throw 'Could not read the dependency list.' }
    $stamp = '.venv/emerald-requirements.txt'
    if (-not (Test-Path -LiteralPath $stamp) -or (Get-Content -LiteralPath $stamp -Raw).Trim() -ne $requirementsHash) {
        Write-Host 'Installing the Python packages used by the builder...'
        & $python -m pip install --disable-pip-version-check --only-binary=:all: -r builder/requirements.txt
        if ($LASTEXITCODE -ne 0) { throw 'Package installation failed. Check your internet connection and Python version, then run again.' }
        Set-Content -LiteralPath $stamp -Value $requirementsHash
    }
    & $python builder/build.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    exit 0
} catch {
    Write-Host "`nBUILD FAILED: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
