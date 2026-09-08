"""HTTP transport seam. Tests replace `post`."""


def post(url, headers, payload):
    raise RuntimeError("no transport configured")
