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
"""C4-M2 Dataspace Wallet Interface — wallet account management.

This module owns the five account routes and the account/retention tasks that
Person A's timer calls (TEAM3-PLAN §14.2 rule 4).  It is package‑free: imported
by `interface.py`, `router.py` and the test suite through the `seam(...)` helper.

The built‑in stand‑ins for account creation/deletion are defined here so that
the test suite can call `seam("modules.c4_m2.accounts").create_wallet_account(...)`
etc. without touching the real middleware.

Milestone M0 — skeleton only (no implementation, no stubs).
"""
from __future__ import annotations


# ----------------------------------------------------------------------
# Public API — the test suite reaches these names through `seam(...)`.
# Do NOT rename without also updating `test_c4_m2_accounts.py` (TEAM3-PLAN §12.1 rule 1).
# ----------------------------------------------------------------------


def create_wallet_account(company_id: str, provider: str, technical_user_id: str | None = None) -> None:
    """Create a wallet account for the given company and provider.

    The test suite drives time manually with ``service.now()`` and
    ``service.run_timer_once()``, so this function is a no‑op at the skeleton
    stage.  Full implementation creates a ``WalletAccount`` row, writes an
    audit entry and emits a ``WalletAccountCreated`` event.
    """
    raise NotImplementedError


def delete_wallet_account(company_id: str, provider: str, technical_user_id: str | None = None) -> None:
    """Delete a wallet account for the given company and provider.

    Skeleton raises ``NotImplementedError``; the final implementation removes
    the ``WalletAccount`` row, writes an audit entry and emits a
    ``WalletAccountDeleted`` event.
    """
    raise NotImplementedError


def get_wallet_account_internal(company_id: str, provider: str) -> None:
    """Look up a wallet account by company and provider.

    Skeleton returns ``None``; the full implementation returns the row or
    ``404`` if the account does not exist.
    """
    raise NotImplementedError


def run_tasks() -> None:
    """Run the account retention / deletion timer tasks.

    Called by ``service.run_timer_once()`` (Person A's timer thread).  The
    skeleton is a no‑op; the full implementation checks ``expires_at`` /
    ``deletion_ordered_at`` and either renews the account or deletes it.
    """
    raise NotImplementedError


def reset() -> None:
    """Clear all internal account state.

    Called at the start of each test to guarantee isolation.
    """
    raise NotImplementedError


# ----------------------------------------------------------------------
# Lazy‑load helpers used by the test suite's `seam(...)` calls.
# The test suite imports these through `seam("modules.c4_m2.accounts")`.
# ----------------------------------------------------------------------


def __getattr__(name: str):
    """Make ``seam("modules.c4_m2.accounts").create_wallet_account(...)`` etc. work.

    This function is only reached when the test suite lazily imports the
    module via the seam helper; it is not a normal import path.
    """
    if name == "create_wallet_account":
        return create_wallet_account
    if name == "delete_wallet_account":
        return delete_wallet_account
    if name == "get_wallet_account_internal":
        return get_wallet_account_internal
    if name == "run_tasks":
        return run_tasks
    if name == "reset":
        return reset
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")