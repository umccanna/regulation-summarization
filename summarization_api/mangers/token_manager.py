from base64 import b64decode
import jwt
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import requests
from config import get_config
import json

class TokenManager:
    def __init__(self):
        self._keys_uri = 'https://milliman.okta.com/oauth2/v1/keys'
        self._audience = get_config("Okta__Audience")
        self._issuer = get_config("Okta__Issuer")

    def parse_token(self, token):
        jwkeys = requests.get(self._keys_uri).json()['keys']
        jwt_header = jwt.get_unverified_header(token)
        token_key_id = jwt_header['kid']
        jwk = [key for key in jwkeys if key['kid'] == token_key_id][0]
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
        pem_key = public_key.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo)
        try:
            token_claims = jwt.decode(token, pem_key, audience=self._audience, issuer=self._issuer, algorithms=[jwt_header["alg"]])
            return token_claims
        except:
            return None