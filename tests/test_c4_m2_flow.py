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
"""Seam test C4-M2 -> C4-M1 -> C12 with the real modules (no wallet fake): `create-wallet`, then
`issue-credentials` (C4-M1 route STUB: ISSUER_MODE OWN with empty ISSUER_ROUTES), default wallet provider CSP with
the built-in CSP stand-in of C4-M2 (C4-M2 README 11.3, 14.1).

Covers: C4-M2 README 10 (event `DataspaceWalletCreated` with all required fields), 9 / C4-M1 11.2 (contract
`get_wallet_info`), C4-M1 README 10 (`CredentialsIssued` once), FRAMEWORK 5.2 + flows.yaml `onboarding` (`register-did`
takes `steps.create-wallet.did` from the event payload; demo.py check "CSP: DID in the directory = wallet DID"),
and C4-M2 README 8.3 (event `WalletAccountCreated`).

The flow test runs the in-process C12 engine (`modules.c12_m1.engine.Engine`) on a flow file derived from the
`onboarding` flow of `spec/C12-M1-ProcessOrchestration/flows.yaml`, reduced to the three steps under test; the
events of the relay are handed to the engine by the test (the app's own engine only knows the real flows).
"""
from __future__ import annotations

import uuid

import yaml

from portal_common import events, spec
from test_c4_m2_common import (
    COMPANIES,
    CSP_URL,
    OSP_A_ID,
    companies,  # noqa: F401  (fixture)
    event_errors,
    osp_factory,  # noqa: F401  (fixture)
    response_errors,
    seam,
    step_input,
)

U1 = COMPANIES["u1"]
BPN = U1["bpn"]
WALLET_DID = f"did:web:csp-wallet.example.org:{BPN}"
ENV = {"STUB_ISSUER_DELAY_SECONDS": "0", "CSP_URL": CSP_URL + "/v1"}   # CSP_URL: C3-M2 core services API
WALLET_CREATED_FIELDS = {"companyId", "did", "walletId", "provider", "didDocumentLocation", "bpn"}   # README 10


def start(osp_factory):
    osp = osp_factory(ENV, csp=True)
    osp.csp_register(BPN, osp_id=OSP_A_ID)        # the company is registered at the CSP by C3-M2 (here: directly)
    return osp, osp.service("svc-c12-m1")


def create_wallet(osp, svc, n: int = 1):
    return osp.post("/api/c4-m2/steps/create-wallet", svc, json=step_input(U1["id"], n))


def issue(osp, svc, n: int = 2):
    return osp.post("/api/c4-m1/steps/issue-credentials", svc, json=step_input(U1["id"], n))


def wallet_created(osp) -> dict:
    evs = osp.events("DataspaceWalletCreated")
    assert len(evs) == 1, f"expected exactly one DataspaceWalletCreated, got {len(evs)}"
    return evs[0]


# ------------------------------------------------------------------------------------ create-wallet
def test_create_wallet_event_has_all_required_fields_and_did_equals_wallet_info(osp_factory, companies):
    # README 10, openapi EventDataspaceWalletCreated; C12 `register-did` needs `did` from this payload
    osp, svc = start(osp_factory)
    r = create_wallet(osp, svc)
    assert r.status_code == 200 and r.json()["state"] == "RUNNING"          # README 8.1: C12 completes on the event
    assert response_errors("c4-m2", "POST", "/steps/create-wallet", 200, r.json()) == []
    ev = wallet_created(osp)
    assert ev["source"] == "urn:c4-m2"
    assert event_errors("c4-m2", ev) == []
    assert WALLET_CREATED_FIELDS <= set(ev["data"]), f"missing: {WALLET_CREATED_FIELDS - set(ev['data'])}"
    info = seam("modules.c4_m2.interface").get_wallet_info(companyId=U1["id"])
    assert ev["data"]["did"] == info["did"] == WALLET_DID
    assert ev["data"]["companyId"] == U1["id"] and ev["data"]["bpn"] == BPN and ev["data"]["provider"] == "CSP"
    assert ev["data"]["walletId"] == info["walletId"] and ev["data"]["didDocumentLocation"]


def test_c4_m1_sees_the_wallet_through_the_contract(osp_factory, companies):
    # C4-M1 README 11.2: status ACTIVE, provider, issuanceMode, did, didDocumentLocation, providerRef
    osp, svc = start(osp_factory)
    create_wallet(osp, svc)
    info = seam("modules.c4_m2.interface").get_wallet_info(companyId=U1["id"])
    assert info["status"] == "ACTIVE" and info["provider"] == "CSP" and info["issuanceMode"] == "HOLDER_REQUESTS"
    assert info["did"] == WALLET_DID and info["didDocumentLocation"] and info["providerRef"]
    from portal_common import neighbours
    via = neighbours.query("c4-m1", "c4-m2", "get_wallet_info", companyId=U1["id"])
    assert via == info
    access = neighbours.query("c4-m1", "c4-m2", "get_holder_access", companyId=U1["id"])
    assert access["issuanceMode"] == "HOLDER_REQUESTS" and access["did"] == WALLET_DID and access["bpn"] == BPN
    assert {"identityApiUrl", "participantContextId", "apiKey"} <= set(access)


# ------------------------------------------------------------------------------------ issue-credentials
def test_credentials_are_issued_exactly_once_after_the_wallet_is_created(osp_factory, companies):
    osp, svc = start(osp_factory)
    create_wallet(osp, svc)
    r = issue(osp, svc)
    assert r.status_code == 200 and r.json()["state"] == "RUNNING"
    seam("modules.c4_m1.service").flush_timers()
    body = osp.get(f"/api/c4-m1/internal/companies/{U1['id']}/credentials", svc).json()
    assert {c["credentialType"]: c["status"] for c in body["credentials"]} == {"BPN": "ISSUED", "MEMBERSHIP": "ISSUED"}
    assert body["run"]["status"] == "DONE"
    done = osp.events("CredentialsIssued")
    assert len(done) == 1
    assert sorted(done[0]["data"]["credentialTypes"]) == ["BPN", "MEMBERSHIP"] and done[0]["data"]["companyId"] == U1["id"]
    assert event_errors("c4-m1", done[0]) == []
    # the OSP sees what C4-M1 took from the wallet contract (README 5: wallet_provider, holder_did)
    items = osp.get("/api/c4-m1/credentials", osp.person("p2-osp", ["OSP Admin"]), params={"companyId": U1["id"]})
    assert {(i["route"], i["walletProvider"], i["holderDid"]) for i in items.json()["items"]} == {("STUB", "CSP", WALLET_DID)}
    assert issue(osp, svc, 3).json()["state"] == "DONE" and len(osp.events("CredentialsIssued")) == 1


def test_event_order_wallet_created_before_credentials_issued(osp_factory, companies):
    osp, svc = start(osp_factory)
    create_wallet(osp, svc)
    issue(osp, svc)
    seam("modules.c4_m1.service").flush_timers()
    types = [e["type"] for e in events.RELAY.log if e["type"] in ("DataspaceWalletCreated", "CredentialsIssued")]
    assert types == ["DataspaceWalletCreated", "CredentialsIssued"]


def test_issue_credentials_before_the_wallet_exists_is_wallet_not_ready(osp_factory, companies):
    # C4-M1 README 8.1: wallet not ACTIVE / missing -> 409 wallet-not-ready (the flow order guarantees create-wallet first)
    osp, svc = start(osp_factory)
    r = issue(osp, svc)
    assert r.status_code == 409 and r.json()["type"] == "urn:c4-m1:problem:wallet-not-ready"
    assert r.json()["retryable"] is False and osp.events("CredentialsIssued") == []


# ------------------------------------------------------------------------- the onboarding flow (C12)
def mini_flow(tmp_path):
    doc = yaml.safe_load(spec.flows_file().read_text(encoding="utf-8"))
    onboarding = next(f for f in doc["flows"] if f["key"] == "onboarding")
    onboarding["steps"] = [s for s in onboarding["steps"] if s["key"] in ("create-wallet", "register-did", "issue-credentials")]
    doc["flows"], doc["lookups"] = [onboarding], {}
    path = tmp_path / "flows.yaml"
    path.write_text(yaml.safe_dump(doc))
    return path


def pump(engine) -> None:
    """Hands the events of the relay to the engine and fires the STUB issuer timers until nothing changes."""
    flush = seam("modules.c4_m1.service").flush_timers
    seen = -1
    while seen != len(events.RELAY.log):
        seen = len(events.RELAY.log)
        for ev in list(events.RELAY.log):
            engine.on_event(ev)
        flush()


def test_onboarding_flow_register_did_gets_the_wallet_did_from_the_event_payload(osp_factory, companies, tmp_path):
    # flows.yaml onboarding: create-wallet (completesOn DataspaceWalletCreated) -> register-did {did: steps.create-wallet.did}
    # -> issue-credentials (completesOn CredentialsIssued); demo.py: "CSP: DID in the directory = wallet DID"
    from modules.c12_m1 import engine as eng
    osp, _svc = start(osp_factory)
    engine = eng.Engine(mini_flow(tmp_path))
    engine.on_event(events.cloudevent("c1-m2", "ApplicationSubmitted", {
        "applicationId": str(uuid.uuid4()), "companyId": U1["id"], "kind": "ONBOARDING", "existingCompany": False,
        "applicantSub": "ebw.test-erika"}))
    pump(engine)
    (proc,) = engine.processes.values()
    states = {s["stepKey"]: s["state"] for s in proc["steps"]}
    assert states == {"create-wallet": "DONE", "register-did": "DONE", "issue-credentials": "DONE"}, proc["steps"]
    assert proc["status"] == "COMPLETED"
    created = wallet_created(osp)
    register = [d for call, d in engine.call_log if call == "c3-m2.register-did"]
    assert len(register) == 1 and register[0]["did"] == created["data"]["did"] == WALLET_DID
    assert register[0]["companyId"] == U1["id"]
    row = osp.csp.core.companies[BPN]
    assert row["did"] == WALLET_DID == seam("modules.c4_m2.interface").get_wallet_info(companyId=U1["id"])["did"]
    assert row["homeOspId"] == OSP_A_ID
    assert len(osp.events("CompanyDidRegistered")) == 1 and len(osp.events("CredentialsIssued")) == 1
    order = [e["type"] for e in events.RELAY.log
             if e["type"] in ("DataspaceWalletCreated", "CompanyDidRegistered", "CredentialsIssued")]
    assert order == ["DataspaceWalletCreated", "CompanyDidRegistered", "CredentialsIssued"]


# ------------------------------------------------------------------------------------- wallet account
def test_create_wallet_account_after_create_wallet_publishes_wallet_account_created(osp_factory, companies):
    # C4-M2 README 8.3 / flows.yaml wallet-access: step input {technicalUserId, companyId} (+ processId, stepRunId);
    # event WalletAccountCreated with technicalUserId, companyId, walletAccountRef (openapi EventWalletAccountFields)
    osp, svc = start(osp_factory)
    create_wallet(osp, svc)
    tu = str(uuid.uuid4())
    r = osp.post("/api/c4-m2/steps/create-wallet-account", svc,
                 json={**step_input(U1["id"], 5), "technicalUserId": tu})
    assert r.status_code == 200, r.text
    evs = osp.events("WalletAccountCreated")
    assert len(evs) == 1 and evs[0]["source"] == "urn:c4-m2"
    assert event_errors("c4-m2", evs[0]) == []
    data = evs[0]["data"]
    assert data["technicalUserId"] == tu and data["companyId"] == U1["id"] and data["walletAccountRef"]
