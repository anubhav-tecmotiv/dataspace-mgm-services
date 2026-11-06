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
"""Routes of C4-M1 (README 6.3): how a credential is triggered at an issuer.

`select_route(wallet)` applies the rules of README 6.3 and returns the route name. A route object has
`name`, `prepare(ctx)` (once per run, before the first order), `order(ctx, credential_type, attempt)`
(returns `(request_ref, issuer_did)`), `cancel(row)` and `revoke(row)` (True = revoked, False = the
route cannot revoke).

Configuration is read from the environment at call time (AGENTS.md rule 6).
"""
from __future__ import annotations

import logging
import os
import threading

from portal_common.problems import Problem

MODULE = "c4-m1"
log = logging.getLogger("c4-m1.routes")

CREDENTIAL_ISSUER, ISSUER_SERVICE, CSP_ISSUER, STUB = "CREDENTIAL_ISSUER", "ISSUER_SERVICE", "CSP_ISSUER", "STUB"
FITS = {CREDENTIAL_ISSUER: "ISSUER_WRITES", ISSUER_SERVICE: "HOLDER_REQUESTS", CSP_ISSUER: "HOLDER_REQUESTS"}


def _no_route(detail: str) -> Problem:
    return Problem(MODULE, 409, "no-issuer-route", detail=detail, retryable=False)


def issuer_routes() -> dict[str, str]:
    """`ISSUER_ROUTES`: `SAP_DIV:CREDENTIAL_ISSUER,IDENTITY_HUB:ISSUER_SERVICE,...` as a dict."""
    out = {}
    for part in os.environ.get("ISSUER_ROUTES", "").split(","):
        if ":" in part:
            provider, route = part.split(":", 1)
            out[provider.strip()] = route.strip()
    return out


def select_route(wallet: dict) -> str:
    """README 6.3, in this order. An own wallet (`BRING_YOUR_OWN`, `CREDENTIAL_OFFER`) has no route in
    version 0.2; it is rejected before rule 2 (OPEN-QUESTIONS.md, case 5 against rule 2)."""
    provider, mode = wallet.get("provider"), wallet.get("issuanceMode")
    if provider == "STUB":                                                   # rule 1
        return STUB
    if provider == "BRING_YOUR_OWN" or mode == "CREDENTIAL_OFFER":
        raise _no_route("an own wallet has no issuer route in version 0.2")
    if os.environ.get("ISSUER_MODE", "OWN") == "CSP":                        # rule 3
        if not os.environ.get("CSP_ISSUER_URL"):
            return STUB
        if mode != "HOLDER_REQUESTS":
            raise _no_route("the CSP issuer issues only into wallets with issuance mode HOLDER_REQUESTS")
        return CSP_ISSUER
    routes = issuer_routes()                                                 # rule 2
    if not os.environ.get("ISSUER_ROUTES", "").strip():
        return STUB
    route = routes.get(provider or "")
    if route is None:
        raise _no_route(f"no entry in ISSUER_ROUTES for the wallet provider {provider}")
    if FITS.get(route) != mode:                                              # rule 4
        raise _no_route(f"route {route} does not fit the issuance mode {mode}")
    return route


# ------------------------------------------------------------------------------------------- STUB
class StubRoute:
    """Built-in stand-in of the issuer (README 11.6): remembers the order and, after
    `STUB_ISSUER_DELAY_SECONDS`, calls the processing of the status report (7.4) in the same process."""

    name = STUB

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.orders: list[dict] = []
        self._pending: list[dict] = []     # {"order", "timer", "fired"}
        self._generation = 0

    def prepare(self, ctx: dict) -> None:
        """No holder access, no holder registration for the stand-in."""

    def order(self, ctx: dict, credential_type: str, attempt: int) -> tuple[str, str | None]:
        order = {"company_id": ctx["company"]["id"], "credential_type": credential_type,
                 "bpn": ctx["company"]["bpn"].upper(), "attempt": attempt}
        try:
            delay = max(0.0, float(os.environ.get("STUB_ISSUER_DELAY_SECONDS", "1")))
        except ValueError:
            delay = 1.0
        with self._lock:
            self.orders.append(order)
            entry = {"order": order, "fired": False, "generation": self._generation}
            entry["timer"] = threading.Timer(delay, self._fire, args=(entry,))
            entry["timer"].daemon = True
            self._pending.append(entry)
            entry["timer"].start()
        return f"stub-{attempt}", None

    def _fire(self, entry: dict) -> None:
        from . import service
        with self._lock:
            if entry["fired"] or entry["generation"] != self._generation:
                return
            entry["fired"] = True
            if entry in self._pending:
                self._pending.remove(entry)
        order = entry["order"]
        fail = {t.strip().upper() for t in os.environ.get("STUB_ISSUER_FAIL_TYPES", "").split(",") if t.strip()}
        failing = order["credential_type"] in fail
        try:
            service.report_status(order["credential_type"].lower(), order["bpn"],
                                  "UNSUCCESSFUL" if failing else "SUCCESSFUL",
                                  "Issuance declined by the stand-in" if failing else None)
        except Problem as e:   # for example the row is gone after a reset
            log.warning("stand-in report for %s/%s not processed: %s", order["bpn"], order["credential_type"], e)

    def flush(self) -> None:
        """Fires every pending timer at once, in order of the orders (tests)."""
        while True:
            with self._lock:
                entry = next((e for e in self._pending if not e["fired"]), None)
            if entry is None:
                return
            entry["timer"].cancel()
            self._fire(entry)

    def cancel(self, row: dict) -> None:
        """An open order is cancelled: nothing to do at the stand-in (a late report revokes at once)."""

    def revoke(self, row: dict) -> bool:
        return True                                                          # README 11.6: always successful

    def reset(self) -> None:
        with self._lock:
            self._generation += 1
            for e in self._pending:
                e["timer"].cancel()
            self._pending.clear()
            self.orders.clear()


_stub = StubRoute()


def stub_orders() -> list[dict]:
    """Every order the STUB route received (tests)."""
    return list(_stub.orders)


def get(name: str):
    if name == STUB:
        return _stub
    raise _no_route(f"route {name} is not available")


def reset() -> None:
    _stub.reset()
