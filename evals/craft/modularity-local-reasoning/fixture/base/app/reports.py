"""Turning stored activity into a report body. Nothing here touches storage."""
from app import accounts

_ACTIVITY = {
    ("u-1", "weekly"): [("mon", 3), ("tue", 5), ("wed", 1)],
    ("u-1", "monthly"): [("w1", 12), ("w2", 8)],
    ("u-3", "weekly"): [("mon", 2)],
}


class UnknownReport(Exception):
    pass


def render(account: accounts.Account, report_id: str) -> bytes:
    rows = _ACTIVITY.get((account.user_id, report_id))
    if rows is None:
        raise UnknownReport(report_id)
    lines = [f"report,{report_id},{account.name}"]
    lines += [f"{label},{count}" for label, count in rows]
    lines.append(f"total,{sum(count for _, count in rows)}")
    return ("\n".join(lines) + "\n").encode("utf-8")
