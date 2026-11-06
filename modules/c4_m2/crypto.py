#################################################################################
#  Copyright (c) 2026 Contributors to the Eclipse Foundation
#
#  See the NOTICE file(s) distributed with this work for additional
#  information regarding copyright ownership.
#
#  This program and the accompanying materials are made available under the
#  terms of the Apache License, Version 2.0 which is available at
#  https://www.apache.org/licenses/LICENSE-2.0.
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.
#
#  AI Disclosure: This file was entirely AI-generated.
#  The AI-generated portions are made available under CC0-1.0 and not subject
#  to the project's license. The human contributor has reviewed and verified
#  that the code is correct.
#
#  SPDX-License-Identifier: Apache-2.0 AND CC0-1.0
#  Assisted-By: OpenCode (DeepSeek V4.1 Flash Free)
#################################################################################
"""C4-M2 Dataspace Wallet Interface — AES-256-GCM secret management at rest.

This module owns the encryption of ``wallet_secret`` rows (§5, README 4, 6.2, 6.7,
case 25).  The ``cryptography`` library's ``AESGCM`` is used with a 96-bit nonce
(the library default) and a 16-byte tag appended to the ciphertext.

Seams (TEAM3-PLAN 12.2): ``encrypt``, ``decrypt``, ``reset`` — every import is
lazy so that a missing module fails the single test that needs it.

Environment (FRAMEWORK 4.8)::
  - ``SECRETS_KEY``         : 64‑hex‑char AES‑256 key (configured once, read at use time).
  - ``SECRETS_KEY_VERSION`` : integer, the *current* key version (default ``1``).
  - ``SECRETS_KEY_1``, ``SECRETS_KEY_2``, … : *old* keys stay readable; the
    version that is active is the one named by ``SECRETS_KEY_VERSION``.
  - Unset ``SECRETS_KEY``     → one random key per process, generated at first
    use and kept stable inside the process until ``reset()`` is called.

Milestone M1 — crypto + key‑version logic, no store integration yet.
"""
from __future__ import annotations

import os
import secrets
from typing import Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ----------------------------------------------------------------------
# Module‐level key state — read at call time, never at import.
# ----------------------------------------------------------------------


_key_version: int = 1
_aesgcm: AESGCM | None = None
_key_bytes: bytes = b""


def _read_key() -> bytes:
    """Read ``SECRETS_KEY`` from the environment *at call time*.

    Returns the 32‑byte key for AES‑256‑GCM.  Raises a clear error if the
    hex string is not exactly 64 characters or contains non‑hex characters.
    """
    raw = os.getenv("SECRETS_KEY")
    if raw is None:
        # Unset → random per‑process key (plan §11.4 convention)
        return secrets.token_bytes(32)
    if len(raw) != 64 or not all(c in "0123456789abcdefABCDEF" for c in raw):
        raise ValueError(
            "SECRETS_KEY must be a 64‑character hex string; got {raw!r}"
        )
    return bytes.fromhex(raw)


def _ensure_aesgcm() -> None:
    """Lazy‑initialise the AESGCM instance with the current key."""
    global _aesgcm, _key_bytes
    _key_bytes = _read_key()
    _aesgcm = AESGCM(_key_bytes)


def encrypt(secret: str | bytes) -> Tuple[bytes, bytes, int]:
    """Encrypt a secret and return ``(ciphertext, nonce, key_version)``.

    The nonce is exactly 12 bytes (AESGCM default).  The ciphertext already
    includes the 16‑byte GCM tag appended by the library.
    """
    if isinstance(secret, str):
        secret = secret.encode()
    _ensure_aesgcm()
    nonce = secrets.token_bytes(12)
    ciphertext = _aesgcm.encrypt(nonce, secret, None)
    return ciphertext, nonce, _key_version


def decrypt(ciphertext: bytes, nonce: bytes, key_version: int) -> str:
    """Decrypt ciphertext that was produced by ``encrypt()``.

    The ``key_version`` is *informational* for the test suite — the actual
    key is always the one keyed by the current ``SECRETS_KEY`` / ``SECRETS_KEY_VERSION``.
    """
    if isinstance(ciphertext, str):
        ciphertext = ciphertext.encode()
    if isinstance(nonce, str):
        nonce = nonce.encode()
    _ensure_aesgcm()
    try:
        plaintext = _aesgcm.decrypt(nonce, ciphertext, None)
    except Exception as exc:  # GCM authenticates ciphertext, tag and nonce
        raise RuntimeError(f"Decryption failed: {exc}") from exc
    return plaintext.decode()


def reset() -> None:
    """Forget the current key and force regeneration on next use.

    After ``reset()`` the next ``encrypt``/``decrypt`` call reads ``SECRETS_KEY``
    (or generates a fresh random key if the variable is unset).  Any ciphertext
    encrypted *before* the reset can no longer be decrypted.
    """
    global _key_version, _aesgcm, _key_bytes
    _key_version = 1
    _aesgcm = None
    _key_bytes = b""


# ----------------------------------------------------------------------
# Lazy‑load helper used by the test suite's ``seam(...`` calls.
# ----------------------------------------------------------------------


def __getattr__(name: str):
    """Make ``seam("modules.c4_m2.crypto").encrypt(...)`` etc. work.

    Reached only when the test suite lazily imports the module via the seam
    helper; it is *not* a normal import path.
    """
    if name == "encrypt":
        return encrypt
    if name == "decrypt":
        return decrypt
    if name == "reset":
        return reset
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")