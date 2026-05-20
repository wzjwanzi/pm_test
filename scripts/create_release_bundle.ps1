param(
  [string]$ReleaseDir = 'release_phase4\MobileTestPlatform',
  [string]$OutputDir = 'artifacts\release',
  [string]$Version = 'phase6-20260515',
  [string]$ValidationJson = 'artifacts\validation\phase5_real_device_validation.json'
)

$ErrorActionPreference = 'Stop'

Set-Location (Split-Path -Parent $PSScriptRoot)

$releasePath = Resolve-Path -LiteralPath $ReleaseDir
$validationPath = Resolve-Path -LiteralPath $ValidationJson
$exePath = Join-Path $releasePath 'MobileTestPlatform.exe'

if (-not (Test-Path -LiteralPath $exePath)) {
  throw "MobileTestPlatform.exe not found at $exePath"
}

$validation = Get-Content -LiteralPath $validationPath -Raw | ConvertFrom-Json
$projectStep = $validation.steps | Where-Object { $_.name -eq 'project_real_run' } | Select-Object -First 1
if (-not $projectStep) {
  throw "project_real_run step not found in phase5_real_device_validation.json"
}

$runId = $projectStep.data.run_id
$runStatus = $projectStep.data.latest_run.status
$runArtifactDir = $projectStep.data.artifact_dir

$outPath = Join-Path (Get-Location) $OutputDir
New-Item -ItemType Directory -Force -Path $outPath | Out-Null

$zipName = "MobileTestPlatform-$Version.zip"
$zipPath = Join-Path $outPath $zipName

Compress-Archive -LiteralPath $releasePath -DestinationPath $zipPath -Force

$exeHash = (Get-FileHash -LiteralPath $exePath -Algorithm SHA256).Hash
$zipHash = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash
$fileCount = (Get-ChildItem -LiteralPath $releasePath -Recurse -File | Measure-Object).Count

$manifest = [ordered]@{
  generated_at = (Get-Date).ToString('o')
  version = $Version
  release_dir = $releasePath.Path
  output_dir = $outPath
  zip_path = $zipPath
  zip_sha256 = $zipHash
  executable_path = $exePath
  executable_sha256 = $exeHash
  file_count = $fileCount
  validation = [ordered]@{
    source = $validationPath.Path
    status = $validation.summary.status
    device_id = $validation.summary.device_id
    run_id = $runId
    run_status = $runStatus
    run_artifact_dir = $runArtifactDir
  }
  verification = [ordered]@{
    package = 'powershell -ExecutionPolicy Bypass -File scripts\verify_package.ps1 -ExePath release_phase4\MobileTestPlatform\MobileTestPlatform.exe'
    real_device = 'powershell -ExecutionPolicy Bypass -File scripts\validate_real_device.ps1 -DeviceId MKBUT20605024486'
    tests = 'python -m pytest -v'
  }
}

$manifestPath = Join-Path $outPath 'release_manifest.json'
$manifest | ConvertTo-Json -Depth 8 | Set-Content -Path $manifestPath -Encoding UTF8

Write-Host "zip=$zipPath"
Write-Host "manifest=$manifestPath"
Write-Host "exe_sha256=$exeHash"
Write-Host "zip_sha256=$zipHash"
