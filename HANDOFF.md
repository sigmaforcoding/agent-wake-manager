# Development status — 2026-10-30

Repository: https://github.com/sigmaforcoding/agent-wake-manager

## Current scope

- Metadata-only Python core, development CLI, event/config/status schemas and synthetic tests.
- Arbitrary instance IDs; pause retains task records and continues lifecycle processing; resume restores current lease intent; reset requires confirmation.
- App icon PNG/ICNS, provenance and macOS packaging script; README preview.
- No installable GUI, service, lease executable, installer, login registration, Scanner, real process observer or power integration in this public development repository.
- The independently installed private experimental version is not replaced by this repository. Its screenshots do not verify this core or unimplemented adapters.
- No formal LICENSE yet: third-party provenance review remains incomplete. No release binary is published.

## Verification

Command: `PYTHONPATH=src python3 -B -m unittest discover -s tests -v`

Latest result on 2026-10-30:

```text
Ran 39 tests in 1.044s

OK
```

Icon packaging was also run on macOS; ICNS round-trip recovered all ten standard representations, from 16×16 to 1024×1024. Tests use synthetic data and temporary directories; no real provider accounts or system power state are tested.

## Workflow and next step

Updates go directly to `main`, as requested by the project owner. See AGENTS.md.

The next scoped core task, when requested, is a synthetic Codex adapter fixture: native event/turn/generation mapping, missing terminal-event behavior and stable owner identity boundaries. Do not install Hooks, read real sessions or start another development stage without a task request.
