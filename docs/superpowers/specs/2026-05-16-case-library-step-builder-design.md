# Case Library and Explicit Step Builder Design

## Goal

Replace the fixed template-only case creation flow with a local case library. Users can create named cases, compose them from explicit start and stop steps, configure per-case IP and traffic parameters, save each case as an individual JSON file, and run selected cases from the desktop exe.

## Current State

The desktop app currently has a `CasesPanel` with a target host field, a fixed template list, and a queue. Cases are represented by `CaseDraft` and converted to legacy dictionaries using `server_action`. Execution is routed through `pm_tests.core.facade.PmTestRunManager`, which builds plans from legacy case dictionaries.

This creates two limitations:

- Users cannot create and persist custom cases as first-class objects.
- Operation ordering and start/stop behavior are hidden behind template strings instead of visible, editable steps.

## Scope

In scope:

- Add a local case library under `cases/`.
- Store each saved case as one JSON file.
- Replace the visible legacy template list with the new case library and step builder.
- Use explicit start/stop steps for base station capture, base station SSH logging, traffic server actions, and phone traffic actions.
- Copy default parameters from runtime settings when a case or step is created, then save those parameters independently in the case file.
- Show runtime command, return output, and progress in one large run console area.

Out of scope:

- External API for creating cases.
- Database storage.
- Multi-user permissions.
- Web/Flask UI.
- Reintroducing Appium.

## Case File Format

Each case is saved as `cases/<safe-name>-<short-id>.json`.

```json
{
  "schema_version": 1,
  "case_id": "case_ab12cd",
  "name": "test1",
  "description": "",
  "created_at": "2026-05-16T10:00:00",
  "updated_at": "2026-05-16T10:05:00",
  "steps": [
    {
      "step_id": "step_001",
      "action": "base_web_capture_start",
      "label": "基站 Web-开始抓包",
      "enabled": true,
      "params": {
        "capture_signal_enabled": true,
        "capture_data_enabled": false,
        "capture_fapi_interface": "FAPI1",
        "download_dir": "D:\\test\\autopm_system\\log"
      }
    }
  ]
}
```

The saved parameters are owned by the case. Changing global runtime settings later does not mutate saved cases.

## Standard Actions

The step builder uses these canonical action IDs:

- `base_web_capture_start`
- `base_web_capture_stop`
- `base_web_collect_log`
- `base_ssh_log_start`
- `base_ssh_log_stop`
- `traffic_server_downlink_start`
- `traffic_server_downlink_stop`
- `traffic_server_down_ping_start`
- `traffic_server_down_ping_stop`
- `traffic_server_uplink_receive_start`
- `traffic_server_uplink_receive_stop`
- `phone_downlink_receive_start`
- `phone_downlink_receive_stop`
- `phone_uplink_iperf_start`
- `phone_uplink_iperf_stop`
- `phone_ping`

Start and stop are user-visible steps. The system may still perform emergency cleanup at case end or failure, but it must report that cleanup in the run console.

## Desktop UI

The case builder area has three responsibilities:

1. Case Library
   - List saved cases from `cases/*.json`.
   - Create, copy, rename, delete, and add cases to the execution queue.

2. Step Builder
   - Show the selected case as a vertical ordered step list.
   - Add steps from a step template catalog.
   - Delete, move up, move down, enable, and disable steps.

3. Step Parameters
   - Show editable parameters for the selected step.
   - Use fields appropriate to the action: IP, port, bandwidth, duration, packet length, capture plane, FAPI interface, log directory, ping count, and similar values.

The old visible template list is removed. Predefined workflows become new-format case templates that copy into the case library as editable step arrays.

## Run Console

The results area should prioritize one large run console. It displays progress, commands, return output, and artifact paths in chronological order.

Example:

```text
[1/8] 基站 Web-开始抓包
参数: CP,FAPI1
结果: started

[2/8] 灌包服务器-开始上行收包
命令: ssh root@10.88.149.164 "iperf -s -i 1 -p 7011"
返回: started, log=D:\test\autopm_system\log\...

[3/8] 手机-开始上行灌包
命令: adb -s xxx shell /data/local/tmp/iperf -u -c 10.88.149.164 ...
返回: running
```

Raw JSON can remain available as a secondary detail view, but it is not the primary user feedback.

## Execution Model

The planner accepts saved case `steps` as the primary input. It converts each enabled step into a `StepPlan` in the exact user-defined order. Legacy `server_action` can remain internally for tests or old data, but the desktop UI no longer exposes it.

Adapters must support long-running start/stop sessions:

- Start actions create sessions in the current case execution context.
- Stop actions locate and stop the matching session.
- Missing stop actions are not a save blocker, but the run should warn and perform cleanup at case end.

The run record should preserve:

- Step label.
- Actual command or Web action.
- Parameters used.
- Status.
- Return preview.
- Artifact paths.

## Validation

Case validation rules:

- Case name is required.
- A case must have at least one enabled step.
- Duplicate visible names are allowed only if file IDs differ; the UI should make duplicate handling clear.
- IP, port, bandwidth, duration, and packet length fields receive basic validation.
- Start/stop mismatch produces a warning, not a hard failure.
- Delete requires confirmation.

## Testing

Add focused tests for:

- Case library create, load, save, rename, copy, delete.
- Per-case parameter persistence.
- Step templates copying runtime defaults correctly.
- Planner preserving explicit step order.
- Start/stop adapter session mapping.
- Emergency cleanup warning when a start step has no matching stop.
- Desktop controller operations for saved cases.
- Run console formatting for commands, progress, returns, and artifact paths.

## Migration

On first implementation, existing built-in workflows should be re-created as new case templates:

- Downlink: phone downlink receive start, traffic server downlink start, traffic server downlink stop, phone downlink receive stop.
- Uplink: traffic server uplink receive start, phone uplink iperf start, phone uplink iperf stop, traffic server uplink receive stop.
- Down ping: traffic server down ping start, traffic server down ping stop.
- Full workflow: capture/log/traffic/ping steps with explicit stops.

The UI should not expose the old fixed template list after the new case library is available.
