# Phase 1 Execution Architecture Redesign

Date: 2026-05-14
Project: mobile_automation_platform

## Context

The project is a Python mobile automation platform with Flask and Tkinter entrypoints. Current execution logic is split across large modules and overlapping abstractions:

- `pm_tests/execution.py` contains the active full PM execution manager and owns run state, step sequencing, adapter calls, cleanup, and summaries.
- `pm_tests/service.py`, `pm_tests/models.py`, and `pm_tests/run_manager.py` contain a newer but narrower service/model design focused on MVP ping flows.
- `desktop_app.py` and `templates/index.html` are large UI clients coupled to the current run dictionary shape.
- Real integrations include ADB, SSH via Paramiko, base-station Web APIs, device tcpdump capture, iperf traffic actions, and Android network snapshots.

The working directory is not a git repository, so the design document cannot be committed from this workspace.

## Goal

Phase 1 will replace the duplicated execution abstractions with a single execution core that supports real device, SSH, base-station Web, capture, traffic, and snapshot integrations through explicit adapter ports.

The primary success criterion is a stable task, case, step, result, artifact, and error model that future Web and Tkinter redesign work can consume without parsing free-text logs or depending on implementation details.

## Non-Goals

Phase 1 will not redesign the Web UI or Tkinter UI.

Phase 1 will not clean release/build artifacts, rebuild packaging, or rewrite release documentation.

Phase 1 does not need to preserve the current Flask/Tkinter external contract. Old entrypoints may be broken temporarily or kept as minimal compatibility clients.

Phase 1 will not introduce a database. Run state remains in memory with artifact files written to disk.

## Architecture

The target architecture has four layers:

1. Entry adapters
2. Execution core
3. Domain models
4. Integration adapters

Entry adapters are thin clients for API, Web, or Tkinter flows. They convert requests into `RunPlan` inputs and return `RunRecord` outputs. They do not own execution state.

The execution core owns run lifecycle and sequencing:

- `RunOrchestrator` creates runs, starts background execution, handles stop requests, and builds run summaries.
- `CaseExecutor` executes one case plan, collects step records, evaluates assertions, and writes case artifacts.
- `StepRunner` wraps a single adapter action with start/end timestamps, timeout handling, status normalization, metrics, artifacts, and structured errors.
- `RunStore` stores active and recent run records in memory and indexes artifact directories.

Domain models define typed plans and records. They are the contract between execution, adapters, and future UI clients.

Integration adapters wrap the existing real implementations. They depend on ADB, requests, Paramiko, and current network helpers, but the execution core depends only on port protocols.

## Domain Model

The plan model describes what should happen:

- `RunPlan`: `run_id`, `device_id`, `case_plans`, `settings_snapshot`, `metadata`.
- `CasePlan`: `case_id`, `name`, `step_plans`, `assertions`, `metadata`.
- `StepPlan`: `step_id`, `kind`, `adapter`, `parameters`, `timeout_seconds`, `required`.

The record model describes what happened:

- `RunRecord`: `run_id`, `device_id`, `status`, timestamps, `progress`, `summary`, `artifact_dir`, `case_records`, `error`.
- `CaseRecord`: `case_id`, `name`, `status`, timestamps, `step_records`, `assertion_results`, `pre_snapshot`, `post_snapshot`, `artifact_dir`, `error`.
- `StepRecord`: `step_id`, `kind`, `adapter`, `status`, timestamps, `message`, `metrics`, `artifacts`, `error`.

Valid statuses are:

- `queued`
- `running`
- `passed`
- `failed`
- `error`
- `skipped`
- `stopping`
- `stopped`

Future UI clients must use these statuses instead of parsing human-readable text.

## Error Model

Every adapter failure returns a structured error:

- `code`: stable machine-readable error code.
- `message`: human-readable message, Chinese where useful for users.
- `adapter`: adapter name such as `adb`, `ssh`, `base_web`, `capture`, `traffic`, or `snapshot`.
- `recoverable`: whether retry or continuation may make sense.
- `details`: optional dictionary with command, endpoint, exit code, stderr, response body summary, or file path.

The execution core maps exceptions into this shape before saving records or returning API responses.

## Adapter Ports

The execution core uses these ports:

- `DevicePort`: ADB shell, push, pull, app launch, UI actions.
- `CapturePort`: inspect capture support, start capture, stop capture.
- `BaseWebPort`: collect logs, start base-station capture, download capture or log files.
- `SshPort`: start command stream, stop stream, collect output logs.
- `TrafficPort`: server-side iperf, device-side iperf, ping, uplink/downlink actions.
- `SnapshotPort`: collect network type, signal, cell info, and network info.

Concrete adapters wrap existing code:

- `utils/adb_utils.py`
- `pm_tests/base_web.py`
- `pm_tests/base_ssh.py`
- `pm_tests/traffic_server.py`
- `pm_tests/capture.py` and `pm_tests/packet_capture.py`
- `network/traffic_tester.py`
- `network/network_monitor.py`
- `network/fiveg_tester.py`

Adapters do not manage run lifecycle state. They return normalized results to `StepRunner`.

## Execution Flow

Creating a run builds a `RunPlan` from request input and a runtime settings snapshot.

The orchestrator creates a `RunRecord` in `queued` state, assigns an artifact directory, stores it in `RunStore`, and starts a background worker.

The worker marks the run `running`, then executes each case in order. For each case:

1. Create a case artifact directory.
2. Collect a pre-case snapshot when configured.
3. Execute the ordered step plan through `StepRunner`.
4. Stop or clean up long-running sessions even when a later step fails.
5. Collect a post-case snapshot when configured.
6. Evaluate assertions.
7. Persist `case.json`.

After all cases finish, the orchestrator writes `run.json`, computes summary counts, and marks the run `passed`, `failed`, `error`, or `stopped`.

## Stop And Cleanup

Stop requests set the run to `stopping`. The worker checks this flag between steps and before starting any long-running adapter action.

For running sessions such as SSH log streams, base-station capture, tcpdump, and iperf, `CaseExecutor` owns a cleanup stack. Cleanup is best-effort and each cleanup result is recorded as a step or artifact note.

If cleanup fails, the original failure remains primary and cleanup failures are recorded in `details.cleanup_errors`.

## Artifact Layout

Artifacts are stored under the configured PM artifacts root:

```text
artifacts/test_runs/<run_id>/
  run.json
  cases/
    <case_index>-<case_id>/
      case.json
      steps/
        <step_index>-<step_id>.json
      files/
        *.pcap
        *.log
        *.txt
```

All JSON files are UTF-8 and use `ensure_ascii=False`.

## Migration Approach

The implementation should replace active use of `PmTestRunManager` with the new execution core. Useful pieces from `PMTestService`, `InMemoryRunManager`, and dataclass models may be retained, renamed, or expanded, but the final code should not expose two competing PM execution services.

Existing Flask and Tkinter entrypoints can be reduced to minimal compatibility calls that create `RunPlan` objects and render `RunRecord` output. Full UI redesign is deferred.

Large modules should be split along ownership boundaries:

- Domain models and serialization.
- Run storage and lifecycle.
- Case and step execution.
- Adapter port protocols.
- Concrete real adapters.
- Request parsing and compatibility mapping.

## Testing Strategy

Phase 1 needs focused automated tests around the new core:

- Model serialization preserves Chinese text and artifact paths.
- `RunOrchestrator` transitions through queued, running, passed, failed, stopping, and stopped states.
- `CaseExecutor` records step failures and still runs cleanup.
- `StepRunner` maps adapter success, failure, skip, and timeout into `StepRecord`.
- Fake adapters can execute a representative run without real hardware.
- Request compatibility mapping can convert current PM case payloads into `RunPlan`.

Hardware-dependent tests should be isolated behind adapter tests or manual smoke scripts, not required for normal unit test runs.

## Risks

The biggest implementation risk is changing real ADB, SSH, base-station Web, capture, and iperf behavior while normalizing adapter interfaces. The mitigation is to wrap existing helpers first, then improve internals only when the new port contract requires it.

Another risk is breaking both current UI clients at once. This is acceptable for phase 1, but the implementation should still provide a small compatibility layer so manual verification can create and inspect runs.

## Acceptance Criteria

- There is one active PM execution service used by source entrypoints.
- Run, case, step, result, artifact, and error records use typed models or clearly defined dataclasses.
- Real adapters exist for ADB, SSH, base-station Web, capture, traffic, and snapshots.
- Execution core does not import concrete ADB, Paramiko, requests, or UI modules directly.
- Stop and cleanup behavior is explicit and recorded.
- Unit tests cover core execution with fake adapters.
- A manual smoke path can create a run and read its `RunRecord`.
