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
#  Assisted-By: Claude Code (claude-sonnet-5-5)
"""Storage of C4-M2 behind one interface (README 5, 12.2).

`WalletStore` is the contract; `InMemoryStore` is the implementation of the hackathon (a database store
can replace it later without a change in the service). Keys of the rows are the column names of the
spec tables `dataspace_wallet`, `wallet_secret`, `audit_log`, `step_log`, `wallet_account` and
`wallet_account_credentials`. Rows are detached copies: a caller changes stored state only through
`put_*`. Only ciphertext reaches the store; `dump()` shows bytes as hex.
"""
from __future__ import annotations

import contextlib
import copy
import datetime as dt
import threading
from typing import Any, Iterator, Protocol


class WalletStore(Protocol):
    """Contract of the storage of C4-M2 (TEAM3 plan 12.2)."""

    # wallets (`dataspace_wallet`)
    def get_wallet(self, company_id: str) -> dict | None: ...
    def put_wallet(self, wallet: dict) -> None: ...
    def find_wallet_by_bpn(self, bpn: str) -> dict | None: ...
    def find_wallet_by_did(self, did: str) -> dict | None: ...
    def list_wallets(self, statuses: list[str] | None = None) -> list[dict]: ...

    # secrets (`wallet_secret`)
    def put_secret(self, wallet_id: str, kind: str, url: str, client_id: str, secret_encrypted: bytes,
                   nonce: bytes, key_version: int) -> None: ...
    def get_secret(self, wallet_id: str, kind: str) -> dict | None: ...
    def delete_secrets(self, wallet_id: str) -> None: ...

    # audit log and step log
    def append_audit(self, entry: dict) -> None: ...
    def list_audit(self) -> list[dict]: ...
    def append_step_log(self, entry: dict) -> None: ...
    def list_step_log(self) -> list[dict]: ...

    # one writer per company at a time (README 6.9)
    def transaction(self, company_id: str) -> contextlib.AbstractContextManager: ...

    def dump(self) -> dict: ...
    def reset(self) -> None: ...


def _jsonable(value: Any) -> Any:
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).hex()
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


class InMemoryStore:
    """`WalletStore` in process memory. Thread safe; `transaction` is a re-entrant lock per company."""

    def __init__(self) -> None:
        self._data = threading.RLock()
        self._txn_guard = threading.Lock()
        self._txn: dict[str, threading.RLock] = {}
        self._clear()

    def _clear(self) -> None:
        self._wallets: dict[str, dict] = {}                          # company_id -> row
        self._secrets: dict[tuple[str, str], dict] = {}              # (wallet_id, kind) -> row
        self._audit: list[dict] = []
        self._step_log: list[dict] = []

    # ------------------------------------------------------------------------------------ wallets
    def get_wallet(self, company_id: str) -> dict | None:
        with self._data:
            return copy.deepcopy(self._wallets.get(company_id))

    def put_wallet(self, wallet: dict) -> None:
        row = copy.deepcopy(wallet)
        if isinstance(row.get("bpn"), str):
            row["bpn"] = row["bpn"].upper()
        with self._data:
            self._wallets[row["company_id"]] = row

    def find_wallet_by_bpn(self, bpn: str) -> dict | None:
        wanted = bpn.upper() if isinstance(bpn, str) else bpn
        with self._data:
            return next((copy.deepcopy(w) for w in self._wallets.values() if w.get("bpn") == wanted), None)

    def find_wallet_by_did(self, did: str) -> dict | None:
        if not did:
            return None
        with self._data:
            return next((copy.deepcopy(w) for w in self._wallets.values() if w.get("did") == did), None)

    def list_wallets(self, statuses: list[str] | None = None) -> list[dict]:
        with self._data:
            return [copy.deepcopy(w) for w in self._wallets.values()
                    if statuses is None or w.get("status") in statuses]

    # ------------------------------------------------------------------------------------ secrets
    def put_secret(self, wallet_id: str, kind: str, url: str, client_id: str, secret_encrypted: bytes,
                   nonce: bytes, key_version: int) -> None:
        row = {"wallet_id": wallet_id, "kind": kind, "url": url, "client_id": client_id,
               "secret_encrypted": bytes(secret_encrypted), "nonce": bytes(nonce), "key_version": key_version,
               "created_at": dt.datetime.now(dt.timezone.utc)}
        with self._data:
            self._secrets[(wallet_id, kind)] = row

    def get_secret(self, wallet_id: str, kind: str) -> dict | None:
        with self._data:
            return copy.deepcopy(self._secrets.get((wallet_id, kind)))

    def delete_secrets(self, wallet_id: str) -> None:
        with self._data:
            for key in [k for k in self._secrets if k[0] == wallet_id]:
                del self._secrets[key]

    # ------------------------------------------------------------------- audit log and step log
    def append_audit(self, entry: dict) -> None:
        with self._data:
            self._audit.append(copy.deepcopy(entry))

    def list_audit(self) -> list[dict]:
        with self._data:
            return copy.deepcopy(self._audit)

    def append_step_log(self, entry: dict) -> None:
        with self._data:
            self._step_log.append(copy.deepcopy(entry))

    def list_step_log(self) -> list[dict]:
        with self._data:
            return copy.deepcopy(self._step_log)

    # ------------------------------------------------------------------------------ transactions
    @contextlib.contextmanager
    def transaction(self, company_id: str) -> Iterator[None]:
        with self._txn_guard:
            lock = self._txn.setdefault(company_id, threading.RLock())
        with lock:
            yield

    # ------------------------------------------------------------------------------- dump, reset
    def dump(self) -> dict:
        with self._data:
            return _jsonable({
                "dataspace_wallet": list(self._wallets.values()),
                "wallet_secret": list(self._secrets.values()),
                "audit_log": self._audit,
                "step_log": self._step_log,
            })

    def reset(self) -> None:
        with self._data:
            self._clear()
