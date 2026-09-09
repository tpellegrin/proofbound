# reporting-service

Renders per-account activity reports and keeps their exports so a later download does not repeat the
work.

- `app/api.py` — request handlers
- `app/exports.py` — creating and fetching exports
- `app/reports.py` — rendering a report body
- `app/accounts.py` — accounts and entitlements
- `app/audit.py` — the service's activity record
- `docs/storage-contract.md` — the semantics of the `objectstore` package the service stores exports in

Run the tests with `python -m unittest discover -s tests -t .`.
