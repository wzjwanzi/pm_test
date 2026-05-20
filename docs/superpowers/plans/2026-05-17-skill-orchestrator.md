# Skill Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a local Codex skill that acts as a coordinator for selecting, sequencing, and handing off to other skills without replacing their instructions.

**Architecture:** Add a new personal skill under `C:\Users\admin\.codex\skills\skill-orchestrator\SKILL.md`. The skill will be a lightweight routing layer: inspect the user request, identify applicable process/domain/execution skills, define their order, and stop once the correct specialist skill should take over.

**Tech Stack:** Markdown skill file, Codex local skills directory, PowerShell validation commands, optional subagent pressure scenarios.

---

## File Structure

- Create: `C:\Users\admin\.codex\skills\skill-orchestrator\SKILL.md`
  - Required skill frontmatter and concise routing workflow.
- Optional Create: `C:\Users\admin\.codex\skills\skill-orchestrator\agents\openai.yaml`
  - Only if the local environment expects UI metadata for personal skills.
- Modify: none in the project source tree.
- Test: manual pressure scenarios documented in the implementation notes.

## Design Constraints

- This skill must not duplicate `using-superpowers`; it is not the “use skills before every response” enforcement layer.
- This skill must not override specialist skills such as `brainstorming`, `writing-plans`, `subagent-driven-development`, `systematic-debugging`, or `verification-before-completion`.
- It must explicitly say that requested skills and user instructions take priority.
- It must choose a minimal skill set, not load every skill.
- It must stop and hand off when a specialist skill becomes required.

## Task 1: Baseline Pressure Scenarios

**Files:**
- No file edits.

- [ ] **Step 1: Define pressure scenarios**

Use these scenario prompts for validation:

```text
Scenario A:
User says: "$brainstorming 做一个新功能，然后执行"
Expected routing: brainstorming first; after approval use writing-plans; after plan approval choose subagent-driven-development or executing-plans.

Scenario B:
User says: "这个测试偶现失败，帮我修"
Expected routing: systematic-debugging first; then test-driven-development for the fix; verification-before-completion before final.

Scenario C:
User says: "$writing-plans 写一个技能：指挥所有技能"
Expected routing: writing-plans because explicitly requested; skill-creator/writing-skills are context, not direct implementation unless execution is approved.

Scenario D:
User says: "实现计划第 1-5 项"
Expected routing: executing-plans for inline execution, or subagent-driven-development if user asks for subagents; verification-before-completion at the end.
```

- [ ] **Step 2: Record baseline risks**

Record these failure modes before writing the skill:

```text
- Loading too many skills by default.
- Treating orchestrator as higher priority than explicit user skill requests.
- Skipping brainstorming for creative/product work.
- Starting implementation after a plan request.
- Replacing specialist skill instructions with a generic summary.
```

Expected: A short note in the worker final response; no file is changed yet.

## Task 2: Create Skill Directory and SKILL.md

**Files:**
- Create: `C:\Users\admin\.codex\skills\skill-orchestrator\SKILL.md`

- [ ] **Step 1: Create skill directory**

Run:

```powershell
New-Item -ItemType Directory -Force 'C:\Users\admin\.codex\skills\skill-orchestrator'
```

Expected: directory exists.

- [ ] **Step 2: Write the skill file**

Create `C:\Users\admin\.codex\skills\skill-orchestrator\SKILL.md` with this content:

```markdown
---
name: skill-orchestrator
description: Use when a task may require multiple skills, skill sequencing, skill handoff decisions, or coordination between planning, implementation, review, and verification workflows.
---

# Skill Orchestrator

## Purpose

Use this as a routing layer for multi-skill work. It decides which skills are relevant, what order to use them in, and where to hand off. It does not replace the instructions inside specialist skills.

## Priority Rules

1. User instructions and explicitly named skills win.
2. Mandatory process skills come before implementation skills.
3. Use the smallest skill set that covers the task.
4. Read a specialist skill before acting on that specialist domain.
5. Stop routing when a specialist skill requires a user approval gate.

## Routing Workflow

1. Restate the user goal in one sentence.
2. Identify explicit skills named by the user.
3. Identify mandatory skills by trigger:
   - Creative/product/feature behavior work -> `brainstorming`
   - Multi-step plan before code -> `writing-plans`
   - Bug, failure, unexpected behavior -> `systematic-debugging`
   - Feature or bugfix implementation -> `test-driven-development`
   - Executing an approved plan inline -> `executing-plans`
   - Executing an approved plan with subagents -> `subagent-driven-development`
   - Creating or editing skills -> `skill-creator` and `writing-skills`
   - Pre-final completion claim -> `verification-before-completion`
   - Completion branch/merge/PR cleanup -> `finishing-a-development-branch`
4. Order skills by phase:
   - Understand -> design -> plan -> implement -> review -> verify -> finish.
5. Announce the selected skill sequence in one short line.
6. Invoke only the next required skill, then follow that skill exactly.

## Common Sequences

### New Feature

`brainstorming` -> `writing-plans` -> `subagent-driven-development` or `executing-plans` -> `verification-before-completion`

### Bug Fix

`systematic-debugging` -> `test-driven-development` -> `verification-before-completion`

### Skill Creation

`skill-creator` -> `writing-skills` -> pressure scenarios -> `verification-before-completion`

### Plan Execution

`executing-plans` for inline execution, or `subagent-driven-development` when the user explicitly chooses subagents.

## Handoff Rules

- If `brainstorming` is selected, do not implement until the design approval gate is passed.
- If `writing-plans` is selected, write the plan and offer execution choices instead of coding.
- If `subagent-driven-development` is selected, dispatch one implementation task at a time and review before proceeding.
- If `verification-before-completion` is selected, run concrete verification commands before claiming success.

## Anti-Patterns

- Do not load every skill “just in case.”
- Do not summarize a specialist skill from memory.
- Do not use this skill to bypass approval gates.
- Do not continue implementing when the active skill says to stop and ask the user.
- Do not treat this skill as higher priority than an explicitly requested skill.
```

- [ ] **Step 3: Validate frontmatter**

Run:

```powershell
Get-Content 'C:\Users\admin\.codex\skills\skill-orchestrator\SKILL.md' -TotalCount 8
```

Expected output begins with:

```text
---
name: skill-orchestrator
description: Use when a task may require multiple skills
---
```

## Task 3: Validate Skill Behavior With Pressure Scenarios

**Files:**
- Read: `C:\Users\admin\.codex\skills\skill-orchestrator\SKILL.md`

- [ ] **Step 1: Static check for forbidden shortcuts**

Run:

```powershell
Select-String -Path 'C:\Users\admin\.codex\skills\skill-orchestrator\SKILL.md' -Pattern 'load every skill|replace|bypass|approval'
```

Expected: matches appear only in anti-pattern or handoff warning sections.

- [ ] **Step 2: Scenario A check**

Read the skill and answer this prompt without editing files:

```text
User says: "$brainstorming 做一个新功能，然后执行"
What skill sequence should be announced?
```

Expected answer:

```text
brainstorming -> writing-plans -> subagent-driven-development or executing-plans -> verification-before-completion
```

- [ ] **Step 3: Scenario B check**

Read the skill and answer this prompt without editing files:

```text
User says: "这个测试偶现失败，帮我修"
What skill sequence should be announced?
```

Expected answer:

```text
systematic-debugging -> test-driven-development -> verification-before-completion
```

- [ ] **Step 4: Scenario C check**

Read the skill and answer this prompt without editing files:

```text
User says: "$writing-plans 写一个技能：指挥所有技能"
What is the next action?
```

Expected answer:

```text
Use writing-plans because it was explicitly requested; skill-creator and writing-skills are context for the plan, not permission to implement the skill yet.
```

## Task 4: Optional UI Metadata

**Files:**
- Optional Create: `C:\Users\admin\.codex\skills\skill-orchestrator\agents\openai.yaml`

- [ ] **Step 1: Decide whether metadata is required**

Run:

```powershell
Test-Path 'C:\Users\admin\.codex\skills\skill-orchestrator\agents\openai.yaml'
```

Expected: if the local skill loader does not require `agents/openai.yaml`, skip this task.

- [ ] **Step 2: Create metadata only if required**

If metadata is required by local tooling, create:

```yaml
display_name: Skill Orchestrator
short_description: Chooses and sequences relevant skills for multi-step work.
default_prompt: Decide which skills apply, announce the sequence, and hand off to the next required specialist skill.
```

Expected: no extra README or documentation files are created.

## Task 5: Final Verification

**Files:**
- Verify: `C:\Users\admin\.codex\skills\skill-orchestrator\SKILL.md`

- [ ] **Step 1: Verify skill file exists**

Run:

```powershell
Test-Path 'C:\Users\admin\.codex\skills\skill-orchestrator\SKILL.md'
```

Expected:

```text
True
```

- [ ] **Step 2: Verify no placeholder text**

Run:

```powershell
Select-String -Path 'C:\Users\admin\.codex\skills\skill-orchestrator\SKILL.md' -Pattern 'TBD|TODO|fill in|placeholder' -CaseSensitive:$false
```

Expected: no matches.

- [ ] **Step 3: Verify skill list sees the directory**

Run:

```powershell
Get-ChildItem -Path 'C:\Users\admin\.codex\skills' -Directory | Where-Object { $_.Name -eq 'skill-orchestrator' }
```

Expected: one directory named `skill-orchestrator`.

- [ ] **Step 4: Commit or record no-git status**

Run:

```powershell
git status --short
```

Expected in this workspace: if output says `not a git repository`, record that no commit was made. If the skill directory is tracked by git in another workspace, commit there with:

```bash
git add C:/Users/admin/.codex/skills/skill-orchestrator/SKILL.md
git commit -m "feat: add skill orchestrator"
```

## Self-Review

- Spec coverage: The plan creates a new skill, gives it a clear trigger, defines routing rules, protects specialist skill handoffs, and validates behavior with concrete scenarios.
- Red-flag scan: The plan contains no incomplete placeholders and no instruction to load all skills by default.
- Type/path consistency: The skill name is consistently `skill-orchestrator`; the file path is consistently `C:\Users\admin\.codex\skills\skill-orchestrator\SKILL.md`.
