"""Clock-skew leeway for Auth0 JWT validation."""

import json
import time
import unittest
from unittest.mock import patch

from authlib.jose import jwt
from authlib.jose.rfc7517.jwk import JsonWebKey

from api.auth0_validator import (
    CLOCK_SKEW_LEEWAY_SECONDS,
    Auth0JWTBearerTokenValidator,
)

DOMAIN = "dev-kxp1v6beff35mbat.us.auth0.com"
AUDIENCE = "https://ufc-fantasy-api"
ISSUER = f"https://{DOMAIN}/"


class _FakeJwksResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body


class Auth0ClockSkewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.signing_key = JsonWebKey.generate_key(
            "RSA", 2048, is_private=True, options={"kid": "test-kid"}
        )
        jwks = json.dumps({"keys": [self.signing_key.as_dict(is_private=False)]}).encode()
        with patch("api.auth0_validator.urlopen", return_value=_FakeJwksResponse(jwks)):
            self.validator = Auth0JWTBearerTokenValidator(DOMAIN, AUDIENCE)

    def _token(self, *, iat_offset=0, exp_offset=3600, nbf_offset=None, iss=ISSUER):
        now = int(time.time())
        payload = {
            "iss": iss,
            "aud": AUDIENCE,
            "sub": "auth0|test-user",
            "iat": now + iat_offset,
            "exp": now + exp_offset,
        }
        if nbf_offset is not None:
            payload["nbf"] = now + nbf_offset
        token = jwt.encode(
            {"alg": "RS256", "kid": "test-kid"},
            payload,
            self.signing_key,
        )
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        return token

    def test_accepts_token_issued_a_few_seconds_in_the_future(self) -> None:
        token = self._token(iat_offset=3)
        claims = self.validator.authenticate_token(token)
        self.assertIsNotNone(claims)
        self.assertFalse(claims.is_expired())

    def test_still_rejects_token_issued_beyond_leeway(self) -> None:
        token = self._token(iat_offset=CLOCK_SKEW_LEEWAY_SECONDS + 30)
        self.assertIsNone(self.validator.authenticate_token(token))

    def test_accepts_exp_within_leeway_and_still_rejects_far_past_exp(self) -> None:
        within_leeway = self._token(exp_offset=-10, iat_offset=-120)
        claims = self.validator.authenticate_token(within_leeway)
        self.assertIsNotNone(claims)
        self.assertFalse(claims.is_expired())

        far_expired = self._token(
            exp_offset=-(CLOCK_SKEW_LEEWAY_SECONDS + 30),
            iat_offset=-120,
        )
        self.assertIsNone(self.validator.authenticate_token(far_expired))

    def test_still_rejects_wrong_issuer(self) -> None:
        token = self._token(iss="https://attacker.example/")
        self.assertIsNone(self.validator.authenticate_token(token))
