# Standard Case Template Restore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore built-in case template step order and counts from the older saved desktop cases while keeping current runtime parameter generation.

**Architecture:** Built-in workflow shape stays centralized in `desktop/case_templates.py`. Tests in `tests/test_case_templates.py` define the standard action order for restored templates, while controller tests verify restored templates remain available through the existing case-library/template merge behavior.

**Tech Stack:** Python 3.11, Tkinter desktop layer, pytest, PyInstaller.

---

## File Map

- Modify `tests/test_case_templates.py`: lock restored action order for `下行灌包`, `上行灌包`, `双向灌包`, `RRC 测试用例`, and `入网`.
- Modify `tests/test_desktop_controller.py`: verify restored templates are exposed with saved cases and from a fresh controller.
- Modify `desktop/case_templates.py`: restore standard action sequences and RRC explicit attach/detach workflow.
- Keep `desktop/controller.py` unchanged unless tests show the existing saved-case plus built-in-template merge needs adjustment.

### Task 1: Lock Standard Traffic And Attach Template Actions

**Files:**
- Modify: `tests/test_case_templates.py`

- [ ] **Step 1: Replace the traffic template expectation with the saved-case standards**

Update `test_builtin_case_templates_use_explicit_start_stop_order` to assert:

```python
assert [step.action for step in downlink.steps] == [
    "base_web_capture_start",
    "base_ssh_rate_log_start",
    "common_delay",
    "phone_airplane_mode_off",
    "phone_downlink_receive_start",
    "traffic_server_downlink_start",
    "common_delay",
    "traffic_server_downlink_stop",
    "phone_downlink_receive_stop",
    "phone_airplane_mode_on",
    "common_delay",
    "base_ssh_rate_log_stop",
    "base_web_capture_stop",
]
assert [step.action for step in uplink.steps] == [
    "base_web_capture_start",
    "base_ssh_rate_log_start",
    "common_delay",
    "phone_airplane_mode_off",
    "traffic_server_uplink_receive_start",
    "phone_uplink_iperf_start",
    "common_delay",
    "phone_uplink_iperf_stop",
    "traffic_server_uplink_receive_stop",
    "phone_airplane_mode_on",
    "common_delay",
    "base_ssh_rate_log_stop",
    "base_web_capture_stop",
]
assert [step.action for step in bidirectional.steps] == [
    "base_web_capture_start",
    "base_ssh_rate_log_start",
    "common_delay",
    "phone_airplane_mode_off",
    "phone_downlink_receive_start",
    "traffic_server_downlink_start",
    "traffic_server_uplink_receive_start",
    "phone_uplink_iperf_start",
    "common_delay",
    "traffic_server_downlink_stop",
    "phone_downlink_receive_stop",
    "phone_uplink_iperf_stop",
    "traffic_server_uplink_receive_stop",
    "phone_airplane_mode_on",
    "common_delay",
    "base_ssh_rate_log_stop",
    "base_web_capture_stop",
]
```

- [ ] **Step 2: Add the saved-case standard for the `入网` template**

Add:

```python
def test_builtin_attach_template_uses_saved_case_order():
    attach = next(item for item in build_default_case_templates({}) if item.name == "入网")

    assert [step.action for step in attach.steps] == [
        "base_web_capture_start",
        "phone_airplane_mode_off",
        "phone_airplane_mode_on",
        "base_web_capture_stop",
    ]
```

- [ ] **Step 3: Run the traffic template tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_case_templates.py::test_builtin_case_templates_use_explicit_start_stop_order tests/test_case_templates.py::test_builtin_attach_template_uses_saved_case_order -q
```

Expected: FAIL because current traffic templates have 7, 7, and 11 actions and `入网` is missing.

### Task 2: Restore Traffic And Attach Built-In Templates

**Files:**
- Modify: `desktop/case_templates.py`
- Test: `tests/test_case_templates.py`

- [ ] **Step 1: Restore `下行灌包`, `上行灌包`, and `双向灌包` action lists**

In `build_default_case_templates`, use the action sequences asserted in Task 1.
Keep `_case(...)` and `step_from_template(...)` as the construction path so
current runtime settings still generate hosts, ports, commands, passwords, and
delay defaults.

- [ ] **Step 2: Add the `入网` built-in template**

Add this template in `build_default_case_templates`:

```python
_case(
    "入网",
    [
        "base_web_capture_start",
        "phone_airplane_mode_off",
        "phone_airplane_mode_on",
        "base_web_capture_stop",
    ],
    settings,
),
```

- [ ] **Step 3: Run the traffic template tests and verify they pass**

Run:

```powershell
python -m pytest tests/test_case_templates.py::test_builtin_case_templates_use_explicit_start_stop_order tests/test_case_templates.py::test_builtin_attach_template_uses_saved_case_order -q
```

Expected: PASS.

### Task 3: Restore RRC Explicit Attach And Detach Workflow

**Files:**
- Modify: `tests/test_case_templates.py`
- Modify: `desktop/case_templates.py`

- [ ] **Step 1: Update the RRC failing test to match the old saved-case action order**

Change `test_builtin_rrc_template_contains_logging_repeat_and_cleanup_steps` to assert:

```python
assert [step.action for step in rrc.steps] == [
    "base_web_capture_start",
    "base_ssh_command_start",
    "base_ssh_command_start",
    "base_ssh_command_start",
    "phone_airplane_mode_off",
    "traffic_server_down_ping_start",
    "base_ssh_command_repeat",
    "base_ssh_command_repeat",
    "traffic_server_down_ping_stop",
    "base_ssh_command_stop",
    "base_ssh_command_stop",
    "base_ssh_command_stop",
    "phone_airplane_mode_on",
    "base_web_capture_stop",
]
```

Update assertions that index SSH log/control steps so they point at the new
indices:

```python
assert rrc.steps[4].params == {}
assert rrc.steps[1].params["session_key"] == "rrc_rlc_up"
assert rrc.steps[3].params["session_key"] == "rrc_cpu"
assert rrc.steps[5].params["ping_target"] == "10.6.250.2"
assert rrc.steps[6].params["repeat_count"] == 8
```

- [ ] **Step 2: Run the RRC template test and verify it fails**

Run:

```powershell
python -m pytest tests/test_case_templates.py::test_builtin_rrc_template_contains_logging_repeat_and_cleanup_steps -q
```

Expected: FAIL because current RRC uses `phone_airplane_cycle` at step 2.

- [ ] **Step 3: Restore `_rrc_case` workflow shape**

Build the `steps` list in `_rrc_case` with explicit `phone_airplane_mode_off`
before traffic ping and explicit `phone_airplane_mode_on` before capture stop:

```python
steps = [
    step_from_template("base_web_capture_start", settings),
    CaseStep.new(
        "base_ssh_command_start",
        "基站 SSH-收取 RLC/UP 日志",
        ssh_params(rlc_up_log_command, "rrc_rlc_up", "rrc_rlc_up"),
    ),
    CaseStep.new(
        "base_ssh_command_start",
        "基站 SSH-收取速率日志",
        ssh_params(rate_log_command, "rrc_rate", "rrc_rate"),
    ),
    CaseStep.new(
        "base_ssh_command_start",
        "基站 SSH-收取 CPU 日志",
        ssh_params(cpu_log_command, "rrc_cpu", "rrc_cpu"),
    ),
    step_from_template("phone_airplane_mode_off", settings),
    step_from_template("traffic_server_down_ping_start", settings),
    CaseStep.new(
        "base_ssh_command_repeat",
        "基站 SSH-重复执行 RRC release",
        {
            **ssh_params(rrc_release_command),
            "repeat_count": int(defaults.get("rrc_release_count") or 8),
            "interval_seconds": int(defaults.get("rrc_release_interval_seconds") or 5),
        },
    ),
    CaseStep.new(
        "base_ssh_command_repeat",
        "基站 SSH-重复执行 force-rlc-escape-ctrl",
        {
            **ssh_params(force_rlc_escape_command),
            "repeat_count": int(defaults.get("force_rlc_escape_count") or 3),
            "interval_seconds": int(defaults.get("force_rlc_escape_interval_seconds") or 5),
        },
    ),
    step_from_template("traffic_server_down_ping_stop", settings),
    CaseStep.new(
        "base_ssh_command_stop",
        "基站 SSH-停止 RLC/UP 日志",
        ssh_params("", "rrc_rlc_up"),
    ),
    CaseStep.new(
        "base_ssh_command_stop",
        "基站 SSH-停止速率日志",
        ssh_params("", "rrc_rate"),
    ),
    CaseStep.new(
        "base_ssh_command_stop",
        "基站 SSH-停止 CPU 日志",
        ssh_params("", "rrc_cpu"),
    ),
    step_from_template("phone_airplane_mode_on", settings),
    step_from_template("base_web_capture_stop", settings),
]
```

Keep existing command builders and required-flag behavior attached to the
equivalent start/ping/stop/capture steps.

- [ ] **Step 4: Run the RRC template tests and verify they pass**

Run:

```powershell
python -m pytest tests/test_case_templates.py::test_builtin_rrc_template_contains_logging_repeat_and_cleanup_steps tests/test_case_templates.py::test_rrc_template_uses_documented_ssh_log_and_control_commands -q
```

Expected: PASS.

### Task 4: Verify Template Availability And Full Test Suite

**Files:**
- Modify: `tests/test_desktop_controller.py` if coverage needs the new `入网` availability expectation.

- [ ] **Step 1: Add controller availability coverage for `入网`**

Update the fresh-controller template assertion to inspect names:

```python
names = [item["name"] for item in controller.get_templates()]
assert "双向灌包" in names
assert "入网" in names
```

- [ ] **Step 2: Run targeted template/controller tests**

Run:

```powershell
python -m pytest tests/test_case_templates.py tests/test_desktop_controller.py tests/test_desktop_shell.py tests/test_case_library.py -q
```

Expected: PASS.

- [ ] **Step 3: Run the full source suite**

Run:

```powershell
python -m pytest -q
```

Expected: PASS with existing Tk skip behavior if the current environment skips those tests.

- [ ] **Step 4: Compile touched Python modules**

Run:

```powershell
python -m py_compile desktop\case_templates.py desktop\controller.py
```

Expected: exit code 0.

### Task 5: Package, Sync, Commit, And Push

**Files:**
- Generated: `release/MobileTestPlatform`
- Sync: `D:\test\svn`

- [ ] **Step 1: Rebuild the desktop release**

Run:

```powershell
$targets = @('build_release','release\MobileTestPlatform')
foreach ($t in $targets) {
    if (Test-Path $t) {
        Remove-Item -LiteralPath $t -Recurse -Force -ErrorAction Stop
    }
}
python -m PyInstaller build.spec --clean --noconfirm --distpath release --workpath build_release
```

Expected: PyInstaller reports `Build complete`.

- [ ] **Step 2: Smoke-start the packaged executable**

Run:

```powershell
$exe = 'D:\test\mobile_automation_platform\release\MobileTestPlatform\MobileTestPlatform.exe'
$proc = Start-Process -FilePath $exe -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 4
$alive = -not $proc.HasExited
if ($alive) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
'exe_started=' + $alive
```

Expected: `exe_started=True`.

- [ ] **Step 3: Sync to SVN handoff directory and test there**

Run:

```powershell
robocopy D:\test\mobile_automation_platform D:\test\svn /E /XD .git build_release .pytest_cache __pycache__ /XF *.pyc /NFL /NDL /NJH /NJS /NP
python -m pytest -q
```

Run pytest from `D:\test\svn`. Expected: PASS.

- [ ] **Step 4: Commit and push implementation**

Run:

```powershell
git add desktop/case_templates.py tests/test_case_templates.py tests/test_desktop_controller.py
git commit -m "Restore saved case template workflows"
git push origin main
```

Expected: pushed `main` with the restored template workflow commit.
