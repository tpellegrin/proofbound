"""Producing and fetching report exports.

An export is the rendered bytes of one report for one account, kept so that a later download does
not have to render it again.
"""
import objectstore

from app import accounts, audit, reports


class ExportForbidden(Exception):
    pass


def _key(account: accounts.Account, report_id: str) -> str:
    return f"exports/{account.region}/{account.user_id}/{report_id}.csv"


def create(user_id: str, report_id: str) -> bytes:
    """Render the report and keep it, returning what was stored."""
    account = accounts.load(user_id)
    if not accounts.may_export(account):
        raise ExportForbidden(user_id)
    body = reports.render(account, report_id)
    objectstore.put(_key(account, report_id), body)
    audit.record(user_id, "export.create", report_id)
    return body

_SEQ = {"n": 0}


def fetch(user_id: str, report_id: str):
    account = accounts.load(user_id)
    if not accounts.may_export(account):
        raise ExportForbidden(user_id)
    _SEQ["n"] += 1
    body = reports.render(account, report_id) + f"seq,{_SEQ['n']}\n".encode("utf-8")
    objectstore.put(_key(account, report_id), body)
    return body, _SEQ["n"] == 1
