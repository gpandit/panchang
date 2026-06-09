"""Field-level encryption for the sensitive-data vault.

Birth details and family-member records are encrypted at rest using
Fernet (AES-128-CBC + HMAC) symmetric encryption. The key is **never**
committed: it is read from `API_VAULT_ENCRYPTION_KEY`, which in
staging/production is populated by the managed secret store (see
CONTRIBUTING.md §4). The dev default in `.env.example` is a clearly-marked
placeholder that must be rotated before any non-local use.

Only `vault.py` should import this module — encryption is an
implementation detail of the vault boundary, not a general-purpose utility.
"""

from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


class VaultCipher:
    """Encrypts/decrypts JSON-serialisable payloads with a Fernet key."""

    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode("utf-8"))

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet key — used by ops tooling to provision the
        secret store, never at runtime in the request path."""
        return Fernet.generate_key().decode("utf-8")

    def encrypt_json(self, payload: dict[str, Any]) -> bytes:
        plaintext = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        return self._fernet.encrypt(plaintext)

    def decrypt_json(self, ciphertext: bytes) -> dict[str, Any]:
        try:
            plaintext = self._fernet.decrypt(ciphertext)
        except InvalidToken as exc:
            raise ValueError(
                "vault payload could not be decrypted — wrong key or tampered data"
            ) from exc
        return json.loads(plaintext.decode("utf-8"))
