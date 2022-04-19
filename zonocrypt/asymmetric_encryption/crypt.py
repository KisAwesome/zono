from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding


class public_key:
    def __init__(self, private_key, hash_alg, load_pem=False):

        self.hash_alg = hash_alg
        if not load_pem:
            self.public_key = private_key.public_key()


class private_key:
    def __init__(self, hash_alg):
        self.hash_alg = hash_alg
        self.private_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048)

    def decrypt(self, enc):
        plaintext = private_key.decrypt(enc, padding.OAEP(mgf=padding.MGF1(
            algorithm=self.hash_alg()), algorithm=self.hash_alg(), label=None))
        return plaintext


class zonocrypt:
    SHA224 = hashes.SHA224
    SHA256 = hashes.SHA256
    SHA512 = hashes.SHA512
    SHA512_224 = hashes.SHA512_224
    SHA512_256 = hashes.SHA512_256
    SHA3_224 = hashes.SHA3_224
    SHA3_256 = hashes.SHA3_256
    SHA3_384 = hashes.SHA3_384
    SHA3_512 = hashes.SHA3_512

    hashes = [SHA224, SHA256, SHA512, SHA512_224,
              SHA512_256, SHA3_224, SHA3_256, SHA3_384, SHA3_512]

    def __init__(self, hash_algorithm=SHA256):
        if hash_algorithm not in zonocrypt.hashes:
            raise TypeError('Unsupported hash algorithm')
        self.hash_algorithm = hash_algorithm
        self.private_key = private_key(self.hash_algorithm)
        self.public_key = public_key
