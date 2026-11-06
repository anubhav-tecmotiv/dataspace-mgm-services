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
"""DID checks of C4-M2 (README 6.4): the form of the DID and the content of the DID document.

`check_form` is step 1 (before resolution), `check_document` is step 3. The expected DID of a provider
comes from `providers.get(provider).did_for(bpn)` (imported at call time because `providers.py` is a
separate file); if that file does not exist yet, the configured bases are used directly:
`SAP_DIV_DID_DOCUMENT_BASE_URL` and `IDENTITYHUB_DID_BASE`.
"""
from __future__ import annotations

import os
from urllib.parse import urlsplit

from . import service

INVALID_DID_DOCUMENT = "INVALID_DID_DOCUMENT"
CREDENTIAL_SERVICE = "CredentialService"
_PROVIDERS_WITH_CREDENTIAL_SERVICE = {"IDENTITY_HUB", "CSP"}


def _expected_did(provider: str, bpn: str) -> str | None:
    """The DID the provider must use for `bpn`, None if only the form `did:web:` is checked (CSP)."""
    providers = service.optional_module("providers")
    if providers is not None:
        return providers.get(provider).did_for(bpn)
    if provider == "SAP_DIV":
        base = urlsplit(os.environ.get("SAP_DIV_DID_DOCUMENT_BASE_URL", ""))
        location = (base.netloc + base.path).strip("/").replace("/", ":")
        return f"did:web:{location}:{bpn}" if location else None
    if provider == "IDENTITY_HUB":
        base = os.environ.get("IDENTITYHUB_DID_BASE", "").strip().strip(":")
        return f"did:web:{base}:{bpn}" if base else None
    return None


def check_form(provider: str, did: str, bpn: str) -> bool:
    """README 6.4 step 1. SAP DIV and IdentityHub: exactly the expected DID, case does not matter.
    CSP: only the form `did:web:` (the CSP decides host and path)."""
    if not isinstance(did, str) or not did:
        return False
    if provider == "CSP":
        return did.lower().startswith("did:web:") and len(did) > len("did:web:")
    expected = _expected_did(provider, bpn)
    return expected is not None and did.lower() == expected.lower()


def _non_empty(value: object) -> bool:
    return isinstance(value, str) and value != ""


def _usable_key(method: object) -> bool:
    jwk = method.get("publicKeyJwk") if isinstance(method, dict) else None
    if not isinstance(jwk, dict):
        return False
    if jwk.get("kty") == "EC":
        return all(_non_empty(jwk.get(name)) for name in ("crv", "x", "y"))
    if jwk.get("kty") == "OKP":
        return all(_non_empty(jwk.get(name)) for name in ("crv", "x"))
    return False


def _has_credential_service(document: dict) -> bool:
    services = document.get("service")
    if isinstance(services, dict):
        services = [services]
    if not isinstance(services, list):
        return False
    for entry in services:
        kind = entry.get("type") if isinstance(entry, dict) else None
        if kind == CREDENTIAL_SERVICE or (isinstance(kind, list) and CREDENTIAL_SERVICE in kind):
            return True
    return False


def check_document(provider: str, did: str, document: dict) -> str | None:
    """README 6.4 step 3: None if the document is fine, else `INVALID_DID_DOCUMENT`."""
    if not isinstance(document, dict) or document.get("id") != did:
        return INVALID_DID_DOCUMENT
    methods = document.get("verificationMethod")
    if not isinstance(methods, list) or not any(_usable_key(m) for m in methods):
        return INVALID_DID_DOCUMENT
    if provider in _PROVIDERS_WITH_CREDENTIAL_SERVICE and not _has_credential_service(document):
        return INVALID_DID_DOCUMENT
    return None
