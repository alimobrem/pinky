"""Auth provider abstraction — OpenShift OAuth and external OIDC."""

import os
import ssl
from dataclasses import dataclass
from pathlib import Path

import httpx

_INGRESS_CA = "/etc/pki/tls/ingress/ingress-ca.crt"
_K8S_CA = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"


def _get_ssl_context() -> ssl.SSLContext | bool:
    if os.environ.get("PINKY_DEBUG", "").lower() == "true":
        return False
    ca_files = [p for p in [_INGRESS_CA, _K8S_CA] if Path(p).exists()]
    if not ca_files:
        return True
    ctx = ssl.create_default_context()
    for ca in ca_files:
        ctx.load_verify_locations(ca)
    return ctx


@dataclass(frozen=True)
class ProviderUserInfo:
    provider: str
    subject: str
    email: str | None
    display_name: str | None
    groups: list[str]
    email_verified: bool = False


class AuthProvider:
    def __init__(self, provider_type: str, client_id: str, client_secret: str, issuer_url: str, api_url: str = "") -> None:
        self.provider_type = provider_type
        self.client_id = client_id
        self.client_secret = client_secret
        self.issuer_url = issuer_url.rstrip("/")
        self.api_url = api_url.rstrip("/") if api_url else ""
        self._well_known: dict | None = None

    async def get_well_known(self) -> dict:
        if self._well_known is None:
            async with httpx.AsyncClient(verify=_get_ssl_context()) as client:
                resp = await client.get(f"{self.issuer_url}/.well-known/openid-configuration")
                resp.raise_for_status()
                self._well_known = resp.json()
        return self._well_known or {}

    def get_authorize_url(self, redirect_uri: str, state: str) -> str:
        from urllib.parse import quote

        encoded_redirect = quote(redirect_uri, safe="")
        encoded_client_id = quote(self.client_id, safe="")
        encoded_state = quote(state, safe="")

        if self.provider_type == "openshift":
            return (
                f"{self.issuer_url}/oauth/authorize"
                f"?client_id={encoded_client_id}"
                f"&redirect_uri={encoded_redirect}"
                f"&response_type=code"
                f"&state={encoded_state}"
            )
        return (
            f"{self.issuer_url}/authorize"
            f"?client_id={encoded_client_id}"
            f"&redirect_uri={encoded_redirect}"
            f"&response_type=code"
            f"&scope=openid+email+profile"
            f"&state={encoded_state}"
        )

    async def exchange_code(self, code: str, redirect_uri: str) -> dict:
        if self.provider_type == "openshift":
            token_url = f"{self.issuer_url}/oauth/token"
        else:
            wk = await self.get_well_known()
            token_url = wk["token_endpoint"]

        async with httpx.AsyncClient(verify=_get_ssl_context()) as client:
            resp = await client.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"Token exchange failed ({resp.status_code}): {resp.text[:300]}")
            return resp.json()

    async def get_user_info(self, access_token: str) -> ProviderUserInfo:
        if self.provider_type == "openshift":
            if not self.api_url:
                raise ValueError("openshift_api_url is required — set PINKY_AUTH__OPENSHIFT_API_URL to the K8s API server URL")
            userinfo_url = f"{self.api_url}/apis/user.openshift.io/v1/users/~"
        else:
            wk = await self.get_well_known()
            userinfo_url = wk["userinfo_endpoint"]

        async with httpx.AsyncClient(verify=_get_ssl_context()) as client:
            resp = await client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"User info fetch failed ({resp.status_code}): {resp.text[:300]}")
            data = resp.json()

        if self.provider_type == "openshift":
            return ProviderUserInfo(
                provider="openshift",
                subject=data.get("metadata", {}).get("uid", data.get("metadata", {}).get("name", "")),
                email=None,
                display_name=data.get("metadata", {}).get("name"),
                groups=data.get("groups", []),
            )

        return ProviderUserInfo(
            provider="oidc",
            subject=data.get("sub", ""),
            email=data.get("email"),
            display_name=data.get("name"),
            groups=data.get("groups", []),
            email_verified=data.get("email_verified", False),
        )
