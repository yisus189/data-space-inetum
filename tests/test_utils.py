"""Test utilities for JWT token generation."""
import time
from typing import List, Dict
from jose import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


# Generate a test RSA keypair for signing tokens
def generate_test_keypair():
    """Generate an RSA keypair for testing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Serialize private key in PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    
    # Get public key and serialize
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    
    return private_pem.decode('utf-8'), public_pem.decode('utf-8')


# Test keypair (generated once to avoid slow tests)
TEST_PRIVATE_KEY, TEST_PUBLIC_KEY = generate_test_keypair()


def create_test_jwt(
    username: str = "testuser",
    roles: List[str] = None,
    issuer: str = "http://keycloak:8080/realms/dataspace",
    audience: str = None,
    exp_delta: int = 3600,
    **extra_claims
) -> str:
    """
    Create a test JWT token signed with the test private key.
    
    Args:
        username: Username for the token
        roles: List of roles to include in realm_access.roles
        issuer: Token issuer
        audience: Token audience
        exp_delta: Expiration time in seconds from now
        **extra_claims: Additional claims to include in the token
        
    Returns:
        JWT token string
    """
    if roles is None:
        roles = []
    
    now = int(time.time())
    
    payload = {
        "iss": issuer,
        "sub": f"user-{username}",
        "preferred_username": username,
        "exp": now + exp_delta,
        "iat": now,
        "realm_access": {
            "roles": roles
        },
        **extra_claims
    }
    
    if audience:
        payload["aud"] = audience
    
    # Sign token with RS256
    token = jwt.encode(
        payload,
        TEST_PRIVATE_KEY,
        algorithm="RS256",
        headers={"kid": "test-key-id"}
    )
    
    return token


def create_test_jwks() -> Dict:
    """
    Create a test JWKS (JSON Web Key Set) from the test public key.
    
    Returns:
        JWKS dictionary
    """
    # Import the public key
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
    import base64
    
    public_key_obj = load_pem_public_key(
        TEST_PUBLIC_KEY.encode('utf-8'),
        backend=default_backend()
    )
    
    # Extract the public numbers
    if not isinstance(public_key_obj, RSAPublicKey):
        raise ValueError("Key is not an RSA public key")
    
    public_numbers = public_key_obj.public_numbers()
    
    # Convert to base64url encoding
    def int_to_base64url(num):
        num_bytes = num.to_bytes((num.bit_length() + 7) // 8, byteorder='big')
        return base64.urlsafe_b64encode(num_bytes).rstrip(b'=').decode('utf-8')
    
    n = int_to_base64url(public_numbers.n)
    e = int_to_base64url(public_numbers.e)
    
    # Create JWKS
    jwks = {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "kid": "test-key-id",
                "n": n,
                "e": e,
                "alg": "RS256"
            }
        ]
    }
    
    return jwks
