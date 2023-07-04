from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet
import cryptography
import secrets
import base64
import base58 
import uuid
import time
import os


class IncorrectDecryptionKey(Exception):
    pass

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

    hashes = [
        SHA224,
        SHA256,
        SHA512,
        SHA512_224,
        SHA512_256,
        SHA3_224,
        SHA3_256,
        SHA3_384,
        SHA3_512,
    ]

    def __init__(self, hash_algorithm=SHA512):
        if hash_algorithm not in zonocrypt.hashes:
            raise TypeError("Unsupported hash algorithm")
        self.hash_algorithm = hash_algorithm

    def encrypt(self, entity, key):
        f = Fernet(key)
        encrypted = f.encrypt(entity.encode())
        return encrypted

    def check_valid_key(self, key):
        try:
            dec_base64 = base64.urlsafe_b64decode(key)
        except:
            return False
        if len(dec_base64) == 32:
            return True
        return False

    def encrypt_bytes(self, entity, key):
        f = Fernet(key)
        encrypted = f.encrypt(entity)
        return encrypted

    def decrypt(self, encrypted, key):
        f = Fernet(key)
        try:
            decrypted = f.decrypt(encrypted)
        except cryptography.fernet.InvalidToken:
            raise IncorrectDecryptionKey("Incorrect Decryption key")

        return decrypted.decode("utf-8")

    def create_safe_identifier(self, ref, len=32):
        ref = f"{ref}{secrets.token_bytes(16)}{time.perf_counter()}"
        return base58.b58encode(self.hashing_function(ref, length=len, valid_key=False, salt=os.urandom(32))).decode("utf-8")

    def str_to_valid_key(self, ref):
        salt = "salty".encode()
        password = ref.encode()

        kdf = PBKDF2HMAC(
            algorithm=self.hash_algorithm(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))

        return key

    def decrypt_raw(self, encrypted, key):
        f = Fernet(key)
        try:
            decrypted = f.decrypt(encrypted)
        except cryptography.fernet.InvalidToken:
            raise IncorrectDecryptionKey("Incorrect Decryption key")
        return decrypted

    def __gen_key__(self, ref):
        password_provided = ref
        password = password_provided.encode()
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=self.hash_algorithm(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))

        return key

    def hashing_function(
        self, ref, iterations=100000, length=32, valid_key=True, salt=None
    ):
        if salt is None:
            salt = b''
        if isinstance(ref,str):
            ref = ref.encode()
        kdf = PBKDF2HMAC(
            algorithm=self.hash_algorithm(),
            length=length,
            salt=salt,
            iterations=iterations,
            backend=default_backend(),
        )

        if valid_key:
            return base64.urlsafe_b64encode(kdf.derive(ref))
        else:
            return kdf.derive(ref)

    def gen_key(self):
        return self.__gen_key__(uuid.uuid4().urn)

    def gen_hash(self):
        return self.__gen_key__(secrets.token_urlsafe())

    def check_valid_key(self, key):
        try:
            dec_base64 = base64.urlsafe_b64decode(key)
        except:
            return False
        if len(dec_base64) == 32:
            return True
        return False

    def randint(self):
        byte = os.urandom(16)
        return int.from_bytes(byte, "big")
