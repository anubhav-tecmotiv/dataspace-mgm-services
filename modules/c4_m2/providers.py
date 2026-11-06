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
"""C4-M2 Dataspace Wallet Interface — provider adapter registry.

This module owns the provider choice logic (§6.1, §6.2) and the adapter registry
(§6.11) used by the wallet steps.  It is package‑free: a single file imported
by `interface.py`, `router.py` and the test suite through the `seam(...)` helper.

The built‑in stand‑ins for **SAP_DIV**, **IDENTITY_HUB** and **CSP** are defined
here so that the test suite can call `seam("modules.c4_m2.providers").get("SAP_DIV")`
etc. without touching the real middleware.

Milestone M0 — skeleton only (no implementation, no stubs).
"""
from __future__ import annotations


# ----------------------------------------------------------------------
# Public API — the test suite reaches these names through `seam(...)`.
# Do NOT rename without also updating `test_c4_m2_providers.py` and
# `test_c4_m2_accounts.py` (TEAM3-PLAN §12.1 rule 1).
# ----------------------------------------------------------------------


def get(provider: str) -> None:
    """Return an adapter for the given provider name.

    Valid provider names are ``"SAP_DIV"``, ``"IDENTITY_HUB"`` and ``"CSP"``.
    The actual adapter objects are created on demand by the step implementation.
    """
    raise NotImplementedError


def enabled() -> bool:
    """Return ``True`` if at least one provider is enabled.

    The ``ENABLED_PROVIDERS`` environment variable (``config/osp-*/module-config.json``)
    decides which providers the installation offers.
    """
    raise NotImplementedError


def default_provider() -> str:
    """Return the default provider name.

    ``ENABLED_PROVIDERS`` empty ``→`` ``"CSP"`` (the hackathon default).
    """
    raise NotImplementedError


def orders() -> list[dict[str, str]]:
    """Return the list of wallet orders that have been placed.

    Each entry is ``{"provider": ..., "bpn": ..., "kind": ...}``
    following the TEAM3-PLAN 12.2 convention (not the README wording).
    """
    raise NotImplementedError


def flush_stand_in() -> None:
    """Fire any pending stand‑in callbacks that have been delayed by
    ``STUB_CALLBACK_DELAY_SECONDS``.

    The test suite drives the timer manually with ``service.run_timer_once()``,
    so this function is called explicitly — never on a background timer during
    tests.
    """
    raise NotImplementedError


def reset() -> None:
    """Clear all internal state (orders, timers, stand‑in callbacks).

    Called at the start of each test to guarantee isolation.
    """
    raise NotImplementedError


# ----------------------------------------------------------------------
# Built‑in stand‑in adapters — one per provider.
# ----------------------------------------------------------------------


class _Adapter:
    """Minimal adapter that the stand‑in routes return.

    The real implementation will replace these with adapters that talk to
    SAP DIV, IdentityHub or the CSP wallet API.
    """

    def __init__(self, name: str):
        self.name = name
        self.provider = name


sap_div = _Adapter("SAP_DIV")
identity_hub = _Adapter("IDENTITY_HUB")
csp = _Adapter("CSP")


def get_impl(provider: str) -> _Adapter:
    """Internal helper — map a provider name to its built‑in adapter."""
    return {"SAP_DIV": sap_div, "IDENTITY_HUB": identity_hub, "CSP": csp}[provider]


# ----------------------------------------------------------------------
# Lazy‑load helpers used by the test suite's `seam(...)` calls.
# The test suite imports these through `seam("modules.c4_m2.providers")`.
# ----------------------------------------------------------------------


def __getattr__(name: str):
    """Make ``seam("modules.c4_m2.providers").orders()`` etc. work.

    This function is only reached when the test suite lazily imports the
    module via the seam helper; it is not a normal import path.
    """
    if name == "get":
        return get
    if name == "enabled":
        return enabled
    if name == "default_provider":
        return default_provider
    if name == "orders":
        return orders
    if name == "flush_stand_in":
        return flush_stand_in
    if name == "reset":
        return reset
    if name == "sap_div":
        return sap_div
    if name == "identity_hub":
        return identity_hub
    if name == "csp":
        return csp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")