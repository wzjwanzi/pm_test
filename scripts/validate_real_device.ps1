param(
  [string]$DeviceId = ''
)

$ErrorActionPreference = 'Stop'

Set-Location (Split-Path -Parent $PSScriptRoot)

$artifactDir = Join-Path (Get-Location) 'artifacts\validation'
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
$resultPath = Join-Path $artifactDir 'phase5_real_device_validation.json'
$adb = Join-Path (Get-Location) 'adb.exe'

if (-not (Test-Path $adb)) {
  throw "adb.exe not found at $adb"
}

function Add-Step {
  param(
    [System.Collections.ArrayList]$Steps,
    [string]$Name,
    [bool]$Success,
    [object]$Data = $null,
    [string]$ErrorMessage = ''
  )
  [void]$Steps.Add([ordered]@{
    name = $Name
    success = $Success
    data = $Data
    error = $ErrorMessage
  })
}

$steps = [System.Collections.ArrayList]::new()
$summary = [ordered]@{
  started_at = (Get-Date).ToString('o')
  device_id = $DeviceId
  result_path = $resultPath
}

try {
  Write-Host "== pytest =="
  python -m pytest -q
  Add-Step $steps 'pytest' $true @{ command = 'python -m pytest -q' }

  Write-Host "== adb devices =="
  $devicesText = & $adb devices
  $devices = @()
  foreach ($line in $devicesText) {
    if ($line -match '^([^\s]+)\s+device$') {
      $devices += $Matches[1]
    }
  }
  if (-not $DeviceId) {
    $DeviceId = $devices | Select-Object -First 1
    $summary.device_id = $DeviceId
  }
  if (-not $DeviceId) {
    throw "No connected ADB device found."
  }
  if ($devices -notcontains $DeviceId) {
    throw "Requested device $DeviceId not found. Devices: $($devices -join ', ')"
  }
  Add-Step $steps 'adb_devices' $true @{ devices = $devices; raw = $devicesText }

  Write-Host "== device properties =="
  $model = (& $adb -s $DeviceId shell getprop ro.product.model) -join "`n"
  $android = (& $adb -s $DeviceId shell getprop ro.build.version.release) -join "`n"
  Add-Step $steps 'device_properties' $true @{ model = $model.Trim(); android = $android.Trim() }

  Write-Host "== project validation =="
  $env:PHASE5_DEVICE_ID = $DeviceId
  $pythonOutput = @'
import json
import os
import time
from pathlib import Path

from device import DeviceManager
from pm_tests import PmTestRunManager

device_id = os.environ["PHASE5_DEVICE_ID"]
manager = PmTestRunManager(run_async=True)
device_manager = DeviceManager()

result = {
    "device_id": device_id,
    "devices": device_manager.get_connected_devices(),
}
result["device_manager_error"] = device_manager.last_error

try:
    result["preflight"] = manager.inspect_device(device_id)
except Exception as exc:
    result["preflight"] = {"success": False, "error": str(exc)}

create_result = manager.create_run(
    device_id,
    cases=[
        {
            "name": "Phase5 Ping Only",
            "host": "10.88.149.164",
            "count": 5,
            "capture_enabled": False,
            "ping_enabled": True,
            "server_action": "none",
        }
    ],
)
run = create_result.get("run", create_result)
run_id = run.get("run_id")
result["created_run"] = run
result["run_id"] = run_id

terminal = {"passed", "failed", "error", "stopped", "completed"}
latest = run
for _ in range(30):
    latest = manager.get_run(run_id) or latest
    status = latest.get("status") or latest.get("state")
    if status in terminal:
        break
    time.sleep(1)

result["latest_run"] = latest
artifact_dir = latest.get("artifact_dir") or run.get("artifact_dir")
result["artifact_dir"] = artifact_dir
if artifact_dir:
    run_json = Path(artifact_dir) / "run.json"
    result["run_json"] = str(run_json)
    result["run_json_exists"] = run_json.exists()

print(json.dumps(result, ensure_ascii=False, indent=2))
'@ | python -

  $projectResult = $pythonOutput | Out-String | ConvertFrom-Json
  Add-Step $steps 'project_real_run' $true $projectResult

  $summary.status = 'completed'
}
catch {
  $summary.status = 'failed'
  $summary.error = $_.Exception.Message
  Add-Step $steps 'validation_error' $false $null $_.Exception.Message
  throw
}
finally {
  $summary.finished_at = (Get-Date).ToString('o')
  $doc = [ordered]@{
    summary = $summary
    steps = $steps
  }
  $doc | ConvertTo-Json -Depth 20 | Set-Content -Path $resultPath -Encoding UTF8
  Write-Host "result=$resultPath"
}
