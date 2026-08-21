import json
import time
from urllib.request import urlopen

from authlib.oauth2.rfc7523 import JWTBearerTokenValidator
from authlib.oauth2.rfc7523.validator import JWTBearerToken
from authlib.jose import jwt, JoseError
from authlib.jose.rfc7517.jwk import JsonWebKey

# Allow Auth0's clock to run a few seconds ahead of the API container.
CLOCK_SKEW_LEEWAY_SECONDS = 60


class Auth0JWTBearerToken(JWTBearerToken):
    def is_expired(self):
        exp = self.get("exp")
        if not isinstance(exp, (int, float)):
            return True
        return exp < (time.time() - CLOCK_SKEW_LEEWAY_SECONDS)


class Auth0JWTBearerTokenValidator(JWTBearerTokenValidator):
    token_cls = Auth0JWTBearerToken

    def __init__(self, domain, audience):
        print("VALIDATOR INITIALIZED")
        issuer = f"https://{domain}/"
        jsonurl = urlopen(f"{issuer}.well-known/jwks.json")
        public_key = JsonWebKey.import_key_set(
            json.loads(jsonurl.read())
        )
        super(Auth0JWTBearerTokenValidator, self).__init__(
            public_key
        )
        self.claims_options = {
            "exp": {"essential": True},
            "aud": {"essential": True, "validate": [audience]},
            "iss": {"essential": True, "value": issuer},
        }

    def authenticate_token(self, token_string):
        try:
            claims = jwt.decode(
                token_string, self.public_key,
                claims_options=self.claims_options,
                claims_cls=self.token_cls,
            )
            claims.validate(leeway=CLOCK_SKEW_LEEWAY_SECONDS)
            return claims
        except JoseError:
            return None
