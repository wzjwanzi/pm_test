# Desktop Workbench UI Redesign

## Goal

Redesign the desktop Tkinter UI into a compact, professional three-column workbench inspired by the provided reference screenshot. The new layout should make cases, base stations/devices, execution logs, step results, descriptions, and parameters visible in one operational screen without forcing users to jump between scattered panels.

## Current State

The desktop app currently uses a three-pane `ttk.PanedWindow`:

- Left: devices and case builder.
- Center: run monitor.
- Right: results and runtime settings.

This structure works functionally, but it splits related work across too many boxes. Device/preflight content consumes prime left-side space, while case selection, execution status, results, and settings do not read as one cohesive testing workbench.

## Design Direction

Use a parallel-priority layout:

- Left column: case tree/library and base station/device list.
- Center column: real-time log and step detail table.
- Right column: case summary and editable parameter table.
- Top bar: common actions, concurrency controls, wait time, start/stop, and current status.

This follows the reference image's mental model: choose a case and target on the left, observe execution in the middle, inspect or edit case details on the right.

## Top Toolbar

The header becomes a dense dark-blue command bar with:

- Platform title: `基站自动化测试平台`.
- Case/device actions: refresh base stations, refresh cases, add case, edit case, delete case.
- File actions: FAQ/help, version info, open config, open cases, open results.
- Execution controls: concurrency count, gather-log wait seconds, start, stop, status.

Buttons use one consistent compact size and spacing. The toolbar should not wrap at the default desktop size. Less-used actions can remain on the right side or move into a compact secondary row if the window is narrow.

## Main Workbench Layout

The body uses a horizontal paned layout with stable starting widths:

- Left column: about 360 px.
- Center column: remaining flexible space, highest weight.
- Right column: about 390 px.

Users may resize panes through the paned window. Minimum sizes must prevent text and tables from collapsing into unusable controls.

## Left Column

The left column contains two stacked sections:

1. Case tree/library
   - Shows case groups and cases in a tree-like control or dense list.
   - Supports selecting a case to populate the right-side summary and parameter table.
   - Keeps visible case operations close to the toolbar actions.

2. Base station/device list
   - Shows selectable targets with columns such as selected, name, IP, and user.
   - Replaces the current separate device/preflight block as a primary navigation element.
   - Preflight details should not dominate the first screen. They can appear as a compact status line, detail popup, or lower expandable area.

The left column intentionally keeps both cases and devices visible because the selected workflow is "parallel priority".

## Center Column

The center column is the execution surface:

1. Real-time log
   - Large text area occupying the upper center.
   - Shows timestamped runtime messages, commands, SSH paths, progress, and errors.
   - Should be the largest single area on the screen.

2. Step detail table
   - Lower table with columns: step, step name, condition, expected value, actual value, result, and note.
   - Displays the current case's execution progress and final outcomes.
   - Keeps row height compact and table headers clear.

## Right Column

The right column contains:

1. Case summary
   - Case name and short description.
   - Test purpose.
   - Keyword tags.
   - Related metadata, if available.
   - Scrollable if content is long.

2. Case parameter table
   - Editable table with columns such as group, parameter, and value.
   - Reflects the selected case or selected step.
   - Supports compact inline editing where practical; otherwise selection can open an editor area.

Runtime settings should no longer occupy a permanent large block in the first screen. They should move behind `打开配置` or a compact dialog because they are not part of the core execution loop.

## Visual Style

The app keeps a native Tk desktop feel but receives a stronger platform visual system:

- Dark-blue top bar with white title text.
- Light gray workbench background.
- White or near-white content panels.
- Compact 6-8 px spacing.
- Consistent button width, table row height, and section header styling.
- Font: `Microsoft YaHei UI` where available, with fallback to Tk defaults.
- Avoid decorative cards, gradients, oversized headings, and marketing-style layout.

The target is dense, orderly, and professional rather than sparse or decorative.

## Data Flow

Case selection drives:

- Right-side case summary.
- Right-side parameter table.
- Center step detail table.

Device/base station selection drives:

- Top status.
- Execution target for start.
- Optional preflight/detail output.

Run updates drive:

- Top status.
- Center real-time log.
- Center step detail table.
- Result/open artifact actions.

Existing controller and execution APIs should remain the integration boundary. The redesign should focus on UI layout and presentation, not execution behavior.

## Error Handling

- If no case is selected, the summary and parameter table show an empty but stable state.
- If no device/base station is selected, start execution is blocked with a clear status message.
- If loading cases/devices fails, the affected section shows an inline message and the top status is updated.
- Long text in logs, descriptions, and parameter values must scroll rather than expand the layout.

## Out Of Scope

- Changing execution semantics.
- Reintroducing Flask or web templates.
- Reintroducing Appium.
- Database storage.
- Full drag-and-drop case editing.
- Rebuilding the app in a different UI framework.

## Testing And Verification

Add or update focused Tk tests to verify:

- The top toolbar exists and exposes the main command buttons.
- The main layout has left, center, and right workbench panes.
- The left pane contains both case and base station/device sections.
- The center pane contains real-time log and step detail table.
- The right pane contains case summary and parameter table.
- Runtime settings are not a large permanent first-screen panel.
- Existing case, run, and controller tests still pass.

Manual/source verification should include:

```powershell
python -m py_compile desktop_app.py
```

And a Tk initialization smoke test that constructs `DesktopApp`, checks the main workbench attributes, updates idle tasks, and destroys the root window.

Packaging verification should continue to use the default release path:

```text
D:\test\mobile_automation_platform\release\MobileTestPlatform\MobileTestPlatform.exe
```

## Acceptance Criteria

- The first screen resembles the reference structure: toolbar on top, case/device navigation on the left, log/steps in the center, description/parameters on the right.
- Device/base station content is moved out of the current dominant standalone panel and integrated into the left navigation column.
- The layout is compact but readable at the existing default window size.
- Users can still refresh devices/cases, select a case, select a device, start/stop execution, view logs, view steps, and inspect parameters.
- Existing execution and case-library behavior remains intact.
