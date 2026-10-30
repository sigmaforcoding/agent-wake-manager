# Repository workflow

- Work and publish updates directly on `main`, unless the owner explicitly requests another branch. Do not force-push or rewrite published history.
- Keep this public development repository isolated from installed experimental versions. Never import runtime data, databases, backups, real provider configuration, credentials, conversations or installed `.app` bundles.
- Default to metadata-only input. Do not add conversation scanning, model/API configuration, container plist access or system power modifications.
- Preserve the distinction between synthetic core tests, real provider evidence and physical lid-sleep testing. Do not infer one from another.
- Run the relevant checks before pushing. Core test command: `PYTHONPATH=src python3 -B -m unittest discover -s tests -v`.
- Keep HANDOFF.md current with scope, verified evidence, unresolved limits and the next requested action.
- Do not adopt a formal license or publish release binaries until the pending provenance and distribution work is explicitly completed.
