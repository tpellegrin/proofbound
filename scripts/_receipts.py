"""Append-only observations, separate from authority state (P1, P3, A6.10)."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import uuid


def receipt(run_root, action, result, **identities):
    root = Path(run_root).resolve()
    directory = root / "receipts"
    directory.mkdir(parents=True, exist_ok=True)
    record = {"format": "proofbound-action-receipt-v1", "action": action,
              "observed_at": datetime.now(timezone.utc).isoformat(),
              "process_id": os.getpid(), "run_root": str(root),
              "identities": identities, "result": result}
    path = directory / (uuid.uuid4().hex + ".json")
    with path.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return str(path)


def refusal(args, payload, code):
    run = getattr(args, "run_root", None)
    if run is None:
        project = getattr(args, "project_root", None)
        if project is None: return None
        run = Path(project) / "DeepSeekAndDestroy" / "authorization"
    contract = getattr(args, "contract", None)
    identities = {"phase": getattr(args, "phase_id", None),
                  "task": getattr(args, "task_id", None),
                  "candidate": payload.get("candidate"), "contract": str(contract) if contract else None}
    if contract and Path(contract).is_file():
        identities["contract_sha256"] = hashlib.sha256(Path(contract).read_bytes()).hexdigest()
    return receipt(run, "pb_execution " + args.command,
                   {"returncode": code, "refused": True, **payload}, **identities)
