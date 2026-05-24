$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

function Assert-ReleaseSettingsMatchesSource {
    param(
        [Parameter(Mandatory = $true)][string]$SourcePath,
        [Parameter(Mandatory = $true)][string]$TargetPath
    )

    if (-not (Test-Path -LiteralPath $SourcePath)) {
        return
    }
    if (-not (Test-Path -LiteralPath $TargetPath)) {
        throw "settings.json mismatch after packaging: release settings.json was not copied"
    }

    $source = Get-Content -LiteralPath $SourcePath -Raw -Encoding UTF8 | ConvertFrom-Json
    $target = Get-Content -LiteralPath $TargetPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($source.traffic.server_host -ne $target.traffic.server_host) {
        throw "settings.json mismatch after packaging: traffic.server_host source=$($source.traffic.server_host) release=$($target.traffic.server_host)"
    }
}

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
$templateSource = Join-Path $PSScriptRoot "mobile_platform_config.json"
$templateTarget = Join-Path $PSScriptRoot "release\MobileTestPlatform\mobile_platform_config.json"

if (Test-Path -LiteralPath $settingsSource) {
    Copy-Item -LiteralPath $settingsSource -Destination $settingsTarget -Force
    Assert-ReleaseSettingsMatchesSource -SourcePath $settingsSource -TargetPath $settingsTarget
}
if (Test-Path -LiteralPath $templateSource) {
    Copy-Item -LiteralPath $templateSource -Destination $templateTarget -Force
}

Write-Host ""
Write-Host "Build finished:"
Write-Host "$PSScriptRoot\release\MobileTestPlatform\MobileTestPlatform.exe"
