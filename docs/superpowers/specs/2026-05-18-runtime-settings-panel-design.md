# Runtime Settings Panel Design

## Goal

Make runtime parameter configuration usable and reliable by replacing the JSON editor with four separated business modules: Base Web, Base SSH, Traffic Server, and Phone. Users must be able to save current parameters, see passwords in plain text, and keep the existing runtime `settings.json` compatibility.

## Current State

The desktop app stores runtime settings in `settings.json` through `app_settings.py`.

Current top-level settings groups:

- `base_web`
- `ssh`
- `traffic`
- `iperf`
- `ping`

The current `SettingsPanel` renders one JSON editor per top-level group. This makes the save behavior unclear and forces users to understand the internal settings schema. The current UI also does not match the business modules users think in: Base Web, Base SSH, Traffic Server, and Phone.

## Selected Approach

Use four business tabs with typed form controls while preserving the existing file format.

Tabs:

- Base Web maps to `base_web`
- Base SSH maps to `ssh`
- Traffic Server maps to the `server_*` fields in `traffic`
- Phone maps to `iperf`, `ping`, and the `phone_*` fields in `traffic`

The UI changes the presentation and save workflow, but the runtime services continue to read from `settings.json` through the existing `app_settings.py` API.

## UI Structure

The settings window keeps the existing toolbar controls:

- Reload
- Save Current Module
- Save All
- Reset Defaults

The notebook tabs become:

- Base Web
- Base SSH
- Traffic Server
- Phone

Each tab uses labeled form controls instead of raw JSON text. Password fields are plain text entries, not masked entries.

## Fields

### Base Web

Maps to `base_web`:

- `host`
- `port`
- `username`
- `password`
- `log_download_dir`
- `capture_signal_enabled`
- `capture_data_enabled`
- `capture_fapi_interface`

Derived fields such as `capture_select_msg`, `capture_transmit_ip`, and `capture_download_dir` remain normalized by `app_settings.py`.

### Base SSH

Maps to `ssh`:

- `host`
- `port`
- `username`
- `password`
- `log_output_dir`
- `log_command`
- `connect_timeout`

### Traffic Server

Maps to `traffic` server fields:

- `server_host`
- `server_port`
- `server_username`
- `server_password`
- `server_connect_timeout`
- `server_log_dir`
- `server_downlink_target`
- `server_downlink_port`
- `server_downlink_bandwidth`
- `server_downlink_duration`
- `server_downlink_packet_len`
- `server_uplink_listen_port`
- `server_ping_target`

### Phone

Maps to `iperf`, `ping`, and phone fields in `traffic`:

- `iperf.tool`
- `iperf.host`
- `iperf.port`
- `iperf.bandwidth`
- `iperf.duration`
- `iperf.interval`
- `iperf.packet_len`
- `iperf.protocol`
- `ping.host`
- `ping.count`
- `traffic.phone_uplink_target`
- `traffic.phone_uplink_port`
- `traffic.phone_uplink_bandwidth`
- `traffic.phone_uplink_duration`
- `traffic.phone_uplink_packet_len`
- `traffic.phone_downlink_listen_port`
- `traffic.phone_ping_target`

## Save Behavior

Save Current Module:

- Reads values only from the active tab.
- Loads current persisted settings first.
- Writes the active tab's values into the matching internal groups.
- Saves through `controller.save_settings(...)` or `controller.save_settings_group(...)`.
- Shows a status message that includes the saved module and `settings.json` path.

Save All:

- Reads all four tabs.
- Merges all form values into the current settings object.
- Saves once through `controller.save_settings(...)`.
- Shows a status message that includes the `settings.json` path.

Reload:

- Loads current settings from disk.
- Updates all four tab forms.

Reset Defaults:

- Calls the existing reset API.
- Updates all four tab forms.

Saving settings does not automatically update existing case step parameters. Users continue to use the existing "remap from configuration" action in the case builder when they want current settings copied into the selected case.

## Validation And Errors

Form parsing validates typed fields before saving:

- Integer fields must parse as integers.
- Boolean fields are checkboxes.
- Choice fields are readonly comboboxes.
- Empty passwords are allowed.
- Text fields are trimmed where existing normalization already trims them.

If validation fails, the panel shows a message box naming the invalid field and does not save partial data.

If `settings.json` is missing or invalid, `load_runtime_settings()` continues to fall back to defaults. A later save writes a valid normalized JSON file.

## Testing

Add tests for a small form mapping layer:

- Loading current settings into the four business modules.
- Saving Base Web without changing SSH, Traffic Server, or Phone values.
- Saving Traffic Server without changing Phone `traffic.phone_*` values.
- Saving Phone updates `iperf`, `ping`, and `traffic.phone_*` together.
- Password values remain plain strings.
- Invalid integer fields raise a validation error before persistence.

Run:

- `python -m pytest tests\test_app_settings.py tests\test_case_templates.py tests\test_desktop_controller.py -q`
- `python -m py_compile desktop\widgets\settings.py app_settings.py`

