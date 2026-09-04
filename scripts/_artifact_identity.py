#!/usr/bin/env python3
"""Canonical content identity for Proofbound textual specification artifacts.

The invariant this module exists to hold:

    the same logical committed text artifact has the same Proofbound identity on every
    supported operating system and under every Git checkout configuration.

Specification artifacts are first-class human-readable text files. Git is allowed to
normalize their line endings on checkout, so raw-byte hashing would make identity depend
on `core.autocrlf` — a machine-local setting no engineering record should depend on.
Identity is therefore taken over a canonical form, and that canonical form is a versioned
wire format, not an implementation detail:

    strict UTF-8 decode -> replace CRLF with LF -> encode UTF-8 -> SHA-256

Deliberate limits:

* Only CRLF is folded. A lone CR is content. This matches Git's own `text` normalization
  exactly, so Proofbound and Git agree about which files are "the same text"; and no
  checkout configuration on a supported platform produces lone-CR files, so there is no
  invariant that would justify erasing them.
* No whitespace normalization, no Unicode normalization, no BOM stripping. Wording,
  spacing, blank lines and code points are all content. Hidden normalization would make
  two visibly different documents share one accepted identity.
* Non-UTF-8 input fails. It is never re-decoded under a guessed encoding, because the
  guess would silently determine the recorded identity.

The digest is a plain SHA-256 of the canonical bytes, deliberately unsalted: on an LF
checkout `sha256sum` reproduces a ledger value with no Proofbound code in the loop.
Version confusion is prevented by the ledger recording `ARTIFACT_IDENTITY_FORMAT`
explicitly, not by perturbing the digest.

A SHA-256 here is integrity, not authority: it proves content did not drift, never who
wrote it (see the trust-boundary section of the RFC).
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ARTIFACT_IDENTITY_FORMAT = "proofbound-artifact-text-v1"
SUPPORTED_ARTIFACT_IDENTITY_FORMATS = (ARTIFACT_IDENTITY_FORMAT,)


class ArtifactIdentityError(ValueError):
    """A byte sequence or path cannot be given a Proofbound artifact identity."""


def canonical_text_bytes(raw: bytes) -> bytes:
    """Return the canonical byte form of one textual artifact.

    CR and LF are ASCII and cannot occur inside a UTF-8 multi-byte sequence, so decoding
    before folding is equivalent to folding bytes. It is done in this order anyway, so the
    strict-decode failure happens before any rewriting of the input.
    """
    if not isinstance(raw, (bytes, bytearray)):
        raise ArtifactIdentityError(f"artifact content must be bytes, got {type(raw).__name__}")
    try:
        text = bytes(raw).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ArtifactIdentityError(f"artifact is not valid UTF-8 text: {exc}") from exc
    return text.replace("\r\n", "\n").encode("utf-8")


def artifact_identity(raw: bytes) -> str:
    """Content identity of one textual artifact, as a lowercase hex SHA-256."""
    return hashlib.sha256(canonical_text_bytes(raw)).hexdigest()


def artifact_identity_file(path: Path) -> str:
    """Content identity of an artifact on disk.

    Reads bytes. Never `open(..., "r")`: platform/universal newline handling would make
    the host silently define the wire format.
    """
    path = Path(path)
    try:
        raw = path.read_bytes()
    except IsADirectoryError as exc:
        raise ArtifactIdentityError(f"artifact is a directory, not a text file: {path}") from exc
    except OSError as exc:
        raise ArtifactIdentityError(f"artifact unreadable: {path}: {exc}") from exc
    try:
        return artifact_identity(raw)
    except ArtifactIdentityError as exc:
        raise ArtifactIdentityError(f"{path}: {exc}") from exc
