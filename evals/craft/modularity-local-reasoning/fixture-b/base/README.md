# Orders service

Places orders and announces them to the parts of the service that need to know. Announcement goes
through `eventbus`, a third-party in-process delivery package; what callers may rely on is in
[`docs/eventbus-contract.md`](docs/eventbus-contract.md).

Run the suite with `python3 -m unittest discover -s tests -t .`.
