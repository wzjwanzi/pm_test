param(
  [string]$ExePath = ''
)

$ErrorActionPreference = 'Stop'

Set-Location (Split-Path -Parent $PSScriptRoot)

if ([string]::IsNullOrWhiteSpace($ExePath)) {
  $exePath = Join-Path (Get-Location) 'release\MobileTestPlatform\MobileTestPlatform.exe'
} else {
  $exePath = $ExePath
  if (-not [System.IO.Path]::IsPathRooted($exePath)) {
    $exePath = Join-Path (Get-Location) $exePath
  }
}

if (-not (Test-Path $exePath)) {
  throw "Packaged exe not found: $exePath"
}

Write-Host "exe=$exePath"
$proc = Start-Process -FilePath $exePath -WorkingDirectory (Split-Path -Parent $exePath) -WindowStyle Hidden -PassThru
try {
  Start-Sleep -Seconds 6
  $alive = -not $proc.HasExited
  Write-Host "process_alive=$alive"
  if (-not $alive) {
    throw "Packaged exe exited early with code $($proc.ExitCode)"
  }
}
finally {
  Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
}
