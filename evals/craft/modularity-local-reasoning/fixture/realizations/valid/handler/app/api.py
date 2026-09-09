"""The service's request handlers. Each returns (status, body)."""
import objectstore

from app import accounts, exports, reports


def create_export(user_id: str, report_id: str):
    try:
        body = exports.create(user_id, report_id)
    except accounts.UnknownAccount:
        return 404, b"no such account"
    except exports.ExportForbidden:
        return 403, b"upgrade required"
    except reports.UnknownReport:
        return 404, b"no such report"
    return 201, body


def download_export(user_id: str, report_id: str):
    try:
        try:
            return 200, exports.fetch(user_id, report_id)
        except objectstore.NotFound:
            return 201, exports.create(user_id, report_id)
    except accounts.UnknownAccount:
        return 404, b"no such account"
    except exports.ExportForbidden:
        return 403, b"upgrade required"
    except reports.UnknownReport:
        return 404, b"no such report"
