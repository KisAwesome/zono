import codecs
from random import choice, randint, shuffle
import pickle
import secrets
import os
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet
import cryptography
import base64
import ast

class IncorrectDecryptionKey(Exception):
    pass


class InvalidHash(Exception):
    pass


class InvalidKey(Exception):
    pass


class objcrypt:
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
        if hash_algorithm not in objcrypt.hashes:
            raise TypeError('Unsupported hash algorithm')
        self.hash_algorithm = hash_algorithm

    def check_valid_key(self, key):
        try:
            dec_base64 = base64.urlsafe_b64decode(key)
        except:
            return False
        if len(dec_base64) == 32:
            return True
        return False

    def __encrypt__(self, entity, key):
        if not self.check_valid_key(key):
            raise InvalidKey(
                'Invalid key,key must be 32 long b64 encoded bytes')
        f = Fernet(key)
        encrypted = f.encrypt(entity.encode())
        return encrypted

    def __decrypt__(self, encrypted, key):
        if not self.check_valid_key(key):
            raise InvalidKey(
                'Invalid key,key must be 32 long b64 encoded bytes')
        f = Fernet(key)
        decrypted = f.decrypt(encrypted)
        return decrypted.decode('utf-8')

    def __gen_key__(self, ref):
        password_provided = ref
        password = password_provided.encode()
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(algorithm=self.hash_algorithm(),
                         length=32,
                         salt=salt,
                         iterations=100000,
                         backend=default_backend())
        key = base64.urlsafe_b64encode(kdf.derive(password))

        return key

    def gen_key(self):
        return self.__gen_key__(secrets.token_urlsafe())

    def gen_hash(self):
        return self.__gen_key__(secrets.token_urlsafe())

    def encrypt(self, obj, key):

        serial_obj = pickle.dumps(obj)
        string_obj = codecs.encode(serial_obj, "base64").decode()
        enc = self.__encrypt__(string_obj, key)
        return enc

    def decrypt(self, enc_obj, key):
        if not enc_obj:

            return enc_obj
        if not self.check_valid_key(key):
            raise InvalidKey(
                'Invalid key,key must be 32 long b64 encoded bytes')
        if not enc_obj:
            return enc_obj
        dec_codec = self.__decrypt__(enc_obj, key)
        unpickled = pickle.loads(codecs.decode(dec_codec.encode(), "base64"))
        return unpickled
    
    def encode(self,obj):
        return pickle.dumps(obj)

    def decode(self,encobj):
        return pickle.loads(encobj)
