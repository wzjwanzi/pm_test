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

$releaseDir = Join-Path $PSScriptRoot "release\MobileTestPlatform"
$settingsSource = Join-Path $PSScriptRoot "settings.json"
$settingsTarget = Join-Path $PSScriptRoot "release\MobileTestPlatform\settings.json"
$casesSource = Join-Path $PSScriptRoot "cases"
$casesTarget = Join-Path $PSScriptRoot "release\MobileTestPlatform\cases"

if (Test-Path -LiteralPath $settingsSource) {
    Copy-Item -LiteralPath $settingsSource -Destination $settingsTarget -Force
}
if (Test-Path -LiteralPath $casesSource) {
    Copy-Item -LiteralPath $casesSource -Destination $casesTarget -Recurse -Force
}

Write-Host ""
Write-Host "Build finished:"
Write-Host "$PSScriptRoot\release\MobileTestPlatform\MobileTestPlatform.exe"
