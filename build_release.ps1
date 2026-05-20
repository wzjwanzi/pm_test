$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

$targets = @(
    "build_release",
    "release\MobileTestPlatform"
)

foreach ($target in $targets) {
    if (Test-Path $target) {
        Write-Host "Removing $target ..."
        Remove-Item -LiteralPath $target -Recurse -Force
    }
}

Write-Host "Building MobileTestPlatform ..."
python -m PyInstaller build.spec --clean --noconfirm --distpath release --workpath build_release

Write-Host ""
Write-Host "Build finished:"
Write-Host "$PSScriptRoot\release\MobileTestPlatform\MobileTestPlatform.exe"
