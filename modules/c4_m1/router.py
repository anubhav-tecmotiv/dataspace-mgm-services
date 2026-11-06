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
#  Assisted-By: Claude Code (claude-opus-5-5)
#################################################################################
"""HTTP layer of C4-M1 Credentials (README 6.5, 7, 8, 9): token, permission, then the interface function.

Operations that this router does not implement are answered by the spec-driven fallback of the scaffold.
"""
from __future__ import annotations

from fastapi import Body
from fastapi.responses import Response

from portal_common import standin

from . import interface, service
from .interface import MODULE

STANDIN = True
router = standin.router(MODULE)


def reset() -> None:
    interface.reset()


@router.post("/steps/issue-credentials")
def issue(body: dict = Body(...), _: dict = standin.perm(MODULE, "POST", "/steps/issue-credentials")):
    return interface.issue_credentials(body)


@router.post("/steps/revoke-credentials")
def revoke(body: dict = Body(...), _: dict = standin.perm(MODULE, "POST", "/steps/revoke-credentials")):
    return interface.revoke_credentials(body)


@router.post("/issuer-callbacks/{credentialKind}", status_code=204, response_class=Response)
def issuer_callback(credentialKind: str, body: dict = Body(...),
                    claims: dict = standin.perm(MODULE, "POST", "/issuer-callbacks/{credentialKind}")):
    """README 7.4: token and permission (dependency), kind, body, row handling, audit entry, 204 without body."""
    bpn, status, message = service.validate_report(credentialKind, body)
    interface.report_status(credentialKind, bpn, status, message)
    service.audit(claims, "REPORT_CREDENTIAL_STATUS", None, f"{bpn}:{credentialKind.upper()}", 204)
    return Response(status_code=204)
