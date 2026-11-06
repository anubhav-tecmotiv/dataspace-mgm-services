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
"""Business logic of C4-M2: the single clock, the store, the audit log and the step log.

The router stays a thin HTTP layer and `interface.py` the public functions; the rules of the wallet
(README 6, 8) live here. Every time read of the module goes through `now()` so that tests can move the
clock. `providers` and `accounts` (written by another person) are imported only inside functions.
"""
from __future__ import annotations

import datetime as dt
import importlib
import threading
from types import ModuleType

from .store import InMemoryStore, WalletStore

MODULE = "c4-m2"

_store: WalletStore | None = None
_store_lock = threading.Lock()


def now() -> dt.datetime:
    """The clock of the module: timezone-aware UTC. All time reads go through this function."""
    return dt.datetime.now(dt.timezone.utc)


def get_store() -> WalletStore:
    """The active store (in memory today, a database store later)."""
    global _store
    with _store_lock:
        if _store is None:
            _store = InMemoryStore()
        return _store


def optional_module(name: str) -> ModuleType | None:
    """`modules.c4_m2.<name>` if the file exists, else None; a broken import still raises."""
    full = f"{__package__}.{name}"
    try:
        return importlib.import_module(full)
    except ModuleNotFoundError as error:
        if error.name == full:
            return None
        raise


def reset() -> None:
    """Clear the store and the state held by this file."""
    get_store().reset()


def audit(claims: dict | str | None, operation: str, company_id: str | None, object_id: str | None) -> None:
    """Write an audit entry (README 5 `audit_log`). `claims` is the token claims dict of an HTTP call, or
    the name of the calling module for an in-process call (then the entry holds that name). No secrets."""
    if isinstance(claims, dict):
        sub, azp = claims.get("sub"), claims.get("azp")
    else:
        sub = azp = claims
    get_store().append_audit({"occurred_at": now(), "sub": sub, "azp": azp, "company_id": company_id,
                              "operation": operation, "object_id": object_id})


def log_step(input: dict, step: str, object_id: str | None, state: str) -> None:
    """Write a step-log entry (README 5 `step_log`)."""
    get_store().append_step_log({"step_run_id": input.get("stepRunId"), "process_id": input.get("processId"),
                                 "step": step, "object_id": object_id, "state": state, "occurred_at": now()})
