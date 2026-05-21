# Standard Case Template Restore Design

## Goal

Restore the built-in case templates from the older saved desktop cases so a
fresh package exposes the same tested case workflows after release cleanup or
directory migration.

## Source Of Truth

The step order and step counts for these built-in templates come from the old
saved cases under:

`D:\test\svn\release\MobileTestPlatform\cases`

The saved cases define workflow shape only. Their old host addresses,
passwords, generated commands, step ids, timestamps, and hand-edited runtime
parameter values are not copied into built-in templates.

## Template Scope

These built-in templates will match the old saved case workflows:

| Template | Standard steps |
| --- | ---: |
| `下行灌包` | 13 |
| `上行灌包` | 13 |
| `双向灌包` | 17 |
| `RRC 测试用例` | 14 |
| `入网` | 4 |

Existing built-in templates without old saved-case equivalents remain
available:

- `下行 ping`
- `全流程`

## Standard Workflow Shape

`下行灌包` and `上行灌包` include rate-log collection, attach, test traffic,
detach, surrounding delays, and capture lifecycle.

`双向灌包` includes the same rate-log and phone attach/detach shell around
parallel uplink and downlink traffic:

1. Start base Web capture.
2. Start base SSH rate log.
3. Delay.
4. Turn airplane mode off to attach.
5. Start downlink receive on the phone.
6. Start downlink traffic on the traffic server.
7. Start uplink receive on the traffic server.
8. Start uplink traffic on the phone.
9. Delay for traffic duration.
10. Stop server downlink traffic.
11. Stop phone downlink receive.
12. Stop phone uplink traffic.
13. Stop server uplink receive.
14. Turn airplane mode on to detach.
15. Delay.
16. Stop base SSH rate log.
17. Stop base Web capture.

`RRC 测试用例` follows the saved-case workflow shape with explicit attach and
detach steps instead of replacing both with one airplane-cycle step.

`入网` keeps the saved-case four-step capture, attach, detach, and capture-stop
workflow.

## Parameter Handling

Built-in template steps are still generated through the current action-template
helpers. Runtime settings remain the source of hosts, passwords, ports,
commands, delay defaults, capture options, traffic targets, and per-device
traffic overrides.

Saved cases remain user-owned JSON records. The restore does not overwrite
existing user cases during normal startup.

## Case Library Behavior

The case library continues to show saved cases plus missing built-in templates.
When a saved case name matches a built-in template, the saved case stays first
and the built-in duplicate is not added to the selector.

Release output must not depend on previously generated simplified cases to
expose the standard workflows.

## Tests And Verification

Automated tests will lock down:

- Standard step count and action order for the five restored built-in
  templates.
- Availability of restored built-in templates from a fresh controller.
- Saved cases continuing to coexist with built-in templates.

Verification includes targeted template/controller tests, the full test suite,
desktop release packaging, packaged executable smoke startup, sync to
`D:\test\svn`, and tests in the synced directory.
