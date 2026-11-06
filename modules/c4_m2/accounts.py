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
#################################################################################
"""Wallet accounts of C4-M2 (README 5, 6.3, 6.7, 6.10, 7.2, 7.3, 7.6, 8.2, 8.3, 9.2, 10).

A wallet account is the access of a technical user to the dataspace wallet of its company. The steps
`create-wallet-account` and `delete-wallet-account` are long-running: they answer `RUNNING` when the account was not
complete at the time of the call and the end is reported by an event (README 6.9). Steps and callbacks of one
technical user never run at the same time (a lock per technical user, README 6.9). Time is read only through
`service.now()` at call time. The wallet, the company, the clock, the audit log and the encryption belong to the
core (`service.py`, `crypto.py`); the providers are asked through `providers.get(...)`.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import os
import uuid
from typing import Any

from portal_common import events
from portal_common.problems import Problem

from . import crypto, providers, service

MODULE = "c4-m2"
REQUESTED, ACTIVE, FAILED, DELETING, DELETED = "REQUESTED", "ACTIVE", "FAILED", "DELETING", "DELETED"
NONE, AVAILABLE, RETRIEVED, EXPIRED = "NONE", "AVAILABLE", "RETRIEVED", "EXPIRED"


# --------------------------------------------------------------------------------------- helpers
def _problem(status: int, name: str, detail: str | None = None, retryable: bool = False) -> Problem:
    return Problem(MODULE, status, name, detail=detail, retryable=retryable)


def _number(name: str, default: float) -> float:
    """A positive number from the environment at call time; the default for unset or unusable values."""
    try:
        value = float(os.environ.get(name, "").strip())
    except ValueError:
        return default
    return value if value > 0 else default


def _aware(value: Any) -> dt.datetime | None:
    if isinstance(value, str):
        try:
            value = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, dt.datetime):
        return None
    return value if value.tzinfo else value.replace(tzinfo=dt.timezone.utc)


def _iso(value: Any) -> str | None:
    moment = _aware(value)
    return moment.isoformat() if moment else None


def _lock(technical_user_id: str) -> contextlib.AbstractContextManager:
    """README 6.9: one writer per technical user (the in-memory stand-in of the advisory lock)."""
    return service.get_store().transaction(f"technical-user:{technical_user_id}")


def _uuid(value: Any, name: str) -> str:
    try:
        if not isinstance(value, str):
            raise ValueError
        uuid.UUID(value)
    except ValueError:
        raise _problem(400, "validation", f"{name} must be a UUID") from None
    return value


def _validate(input: dict) -> tuple[str, str]:
    """README 8.2, 8.3 input: `processId`, `stepRunId`, `technicalUserId`, `companyId`; returns the last two."""
    if not isinstance(input, dict):
        raise _problem(400, "validation", "the input must be a JSON object")
    for name in ("processId", "stepRunId"):
        _uuid(input.get(name), name)
    return _uuid(input.get("technicalUserId"), "technicalUserId"), _uuid(input.get("companyId"), "companyId")


def _save(account: dict) -> dict:
    account["changed_at"] = service.now()
    service.get_store().put_account(account)
    return account


def _result(account: dict) -> dict:
    """README 8.2 and 8.3 result (openapi `StepResultWalletAccount`); no secrets."""
    result = {"walletAccountRef": account["id"], "technicalUserId": account["technical_user_id"],
              "companyId": account["company_id"], "provider": account["provider"], "status": account["status"]}
    if account.get("failure_reason"):
        result["failureReason"] = account["failure_reason"]
    return result


def _reply(input: dict, step: str, state: str, account: dict) -> dict:
    service.log_step(input, step, account["id"], state)
    return {"stepRunId": input["stepRunId"], "state": state, "result": _result(account)}


# ------------------------------------------------------------------------------------------ views
def _view(account: dict) -> dict:
    """README 7.2 and 9.2 body (openapi `WalletAccount`): the state of the credentials, never the credentials."""
    expires = None
    if account.get("credentials_state") == AVAILABLE:
        row = service.get_store().get_account_credentials(account["id"])
        expires = _iso(row["expires_at"]) if row else None
    return {"walletAccountRef": account["id"], "technicalUserId": account["technical_user_id"],
            "companyId": account["company_id"], "provider": account["provider"], "status": account["status"],
            "failureReason": account.get("failure_reason"), "credentialsState": account["credentials_state"],
            "credentialsExpireAt": expires, "createdAt": _iso(account.get("created_at")),
            "changedAt": _iso(account.get("changed_at"))}


def _current(technical_user_id: str) -> dict:
    """README 7.2 step 2: the row with a status other than `DELETED`, otherwise the latest; none is 404."""
    account = service.get_store().get_account(technical_user_id)
    if account is None:
        raise _problem(404, "not-found", "no wallet account for this technical user")
    return account


def get_wallet_account_internal(*, technicalUserId: str) -> dict:
    """Query `getWalletAccountInternal` (README 9.2): as 7.2, without the check of the company."""
    return _view(_current(technicalUserId))


def view_wallet_account(technical_user_id: str, claims: dict) -> dict:
    """`GET /technical-users/{id}/wallet-account` (README 7.2): another company's account stays invisible (404)."""
    account = _current(technical_user_id)
    if not claims.get("company_id") or claims["company_id"] != account["company_id"]:
        raise _problem(404, "not-found", "no wallet account for this technical user")
    return _view(account)
