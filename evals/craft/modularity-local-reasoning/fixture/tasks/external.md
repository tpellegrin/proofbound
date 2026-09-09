# Task — make downloading an export produce one if it is not there yet

Today `download_export` only works after `create_export` has been called. If a client asks for an
export that was never created, the request fails instead of producing the report it asked for.

Change the service so that `app.api.download_export(user_id, report_id)` returns the export whether
or not it already exists:

- if an export is already stored for that account and report, return it with status `200`;
- if it is not, produce it, store it, and return it with status `201`;
- entitlement still applies: an account that may not export gets `403` and nothing is stored;
- an unknown account or unknown report still gets `404`;
- calling `download_export` twice in a row for the same account and report must return the same
  bytes both times, and must not leave a different export stored than the one it returned.

`create_export` keeps its current behaviour. The service's existing tests must still pass.
