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


def fetch(user_id: str, report_id: str) -> bytes:
    """Return a previously created export."""
    account = accounts.load(user_id)
    body = objectstore.get(_key(account, report_id))
    audit.record(user_id, "export.fetch", report_id)
    return body


def fetch_or_create(user_id: str, report_id: str):
    """Return the stored export, producing one first if there is none.

    Reports whether the export already existed, so the caller can distinguish returning something
    from having just made it.
    """
    account = accounts.load(user_id)
    try:
        body = objectstore.get(_key(account, report_id))
    except objectstore.NotFound:
        return False, create(user_id, report_id)
    audit.record(user_id, "export.fetch", report_id)
    return True, body
