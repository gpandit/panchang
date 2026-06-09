"""OAuth/OIDC identity verification for Google and Apple sign-in.

Real verification (production) validates the provider's signed identity
token against its published JWKS via Authlib and extracts `(subject, email)`.
That network/JWKS-fetching path is intentionally kept behind the
`IdentityVerifier` protocol so the auth service — and its tests — depend on
*verified identity*, not on a specific HTTP/JWKS flow. Wire the concrete
Authlib-backed verifiers at app start-up; tests inject `StaticVerifier`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ExternalIdentity:
    subject: str
    email: str | None = None


class IdentityVerifier(Protocol):
    """Verifies a provider identity token and returns the external identity."""

    def verify(self, identity_token: str) -> ExternalIdentity: ...


class InvalidIdentityToken(Exception):
    pass


class StaticVerifier:
    """Test/dev verifier: a fixed lookup table of token -> identity.

    Production wires `GoogleVerifier`/`AppleVerifier` (Authlib + JWKS)
    instead — never this class.
    """

    def __init__(self, tokens: dict[str, ExternalIdentity]) -> None:
        self._tokens = tokens

    def verify(self, identity_token: str) -> ExternalIdentity:
        try:
            return self._tokens[identity_token]
        except KeyError as exc:
            raise InvalidIdentityToken("identity token not recognised") from exc


class GoogleVerifier:
    """Production verifier — validates a Google ID token's signature, issuer
    (`accounts.google.com`), audience (our client id) and expiry against
    Google's published JWKS via Authlib, then returns the verified subject.

    Network/JWKS plumbing is deliberately not implemented in Stage 2; wire it
    here when the OAuth client credentials are provisioned in the secret store.
    """

    def __init__(self, client_id: str) -> None:
        self._client_id = client_id

    def verify(self, identity_token: str) -> ExternalIdentity:
        raise NotImplementedError(
            "GoogleVerifier requires live JWKS verification — provision "
            "OAuth credentials and wire Authlib before enabling Google sign-in"
        )


class AppleVerifier:
    """Production verifier — validates an Apple identity token against
    Apple's published JWKS (`appleid.apple.com`). See `GoogleVerifier` for
    why this is stubbed pending credential provisioning."""

    def __init__(self, client_id: str) -> None:
        self._client_id = client_id

    def verify(self, identity_token: str) -> ExternalIdentity:
        raise NotImplementedError(
            "AppleVerifier requires live JWKS verification — provision "
            "OAuth credentials and wire Authlib before enabling Apple sign-in"
        )
