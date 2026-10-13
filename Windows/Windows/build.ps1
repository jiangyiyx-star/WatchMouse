param(
    [switch]$SkipInstall
)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding
Set-Location -LiteralPath $PSScriptRoot
$venvPath = Join-Path $PSScriptRoot '.build-venv'
$pythonPath = Join-Path $venvPath 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv $venvPath
    } else {
        & python -m venv $venvPath
    }
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ is required. Install Python with Add to PATH enabled.' }
}
if (-not $SkipInstall) {
    & $pythonPath -m pip install --disable-pip-version-check -r (Join-Path $PSScriptRoot 'requirements-build.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Failed to install build dependencies.' }
}
$requiredAssets = @('remote.html', 'remote.js', 'remote.css')
foreach ($asset in $requiredAssets) {
    if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $asset))) { throw "Missing frontend asset: $asset" }
}
$version = (& $pythonPath -c 'import receiver; print(receiver.VERSION)').Trim()
if ($LASTEXITCODE -ne 0 -or $version -notmatch '^\d+\.\d+(\.\d+)?$') { throw 'Unable to read a valid release version.' }
$exeName = "WatchMouse-$version"
$executablePath = Join-Path $PSScriptRoot "dist\$exeName.exe"
$arguments = @('-m', 'PyInstaller', '--noconfirm', '--clean', '--onefile', '--windowed', '--name', $exeName, '--hidden-import', 'qrcode.image.pil', '--hidden-import', 'PIL.ImageTk')
$assetPatterns = @('remote.html', 'remote.js', 'remote.css', 'app.ico', 'manifest*.json', '*.webmanifest', 'icon*.svg', 'icon*.png', 'sw.js', 'service-worker.js', 'watch.html', 'watch.js', 'watch.css')
$assets = foreach ($pattern in $assetPatterns) { Get-ChildItem -LiteralPath $PSScriptRoot -Filter $pattern -File }
foreach ($asset in ($assets | Sort-Object FullName -Unique)) {
    $arguments += @('--add-data', "$($asset.FullName);.")
}
$repositoryRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
foreach ($notice in @('LICENSE', 'THIRD_PARTY_LICENSES.txt')) {
    $noticePath = Join-Path $repositoryRoot $notice
    if (-not (Test-Path -LiteralPath $noticePath)) { throw "Missing license notice: $notice" }
    $arguments += @('--add-data', "$noticePath;.")
}
$iconPath = Join-Path $PSScriptRoot 'app.ico'
if (Test-Path -LiteralPath $iconPath) { $arguments += @('--icon', $iconPath) }
$arguments += (Join-Path $PSScriptRoot 'app.py')
& $pythonPath @arguments
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
& $pythonPath (Join-Path $PSScriptRoot 'verify_build.py') --exe $executablePath
if ($LASTEXITCODE -ne 0) { throw 'Built executable does not match current sources. Rebuild after source edits finish.' }
Copy-Item -LiteralPath $executablePath -Destination (Join-Path $PSScriptRoot 'dist\WatchMouse.exe') -Force
Write-Host "Ready: $executablePath"
