import base64
import cryptography
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from random import choice, randint, shuffle
import os
import secrets


class IncorrectDecryptionKey(Exception):
    pass


class InvalidHash(Exception):
    pass


class InvalidKey(Exception):
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

    hashes = [SHA224, SHA256, SHA512, SHA512_224,
              SHA512_256, SHA3_224, SHA3_256, SHA3_384, SHA3_512]

    def __init__(self, hash_algorithm=SHA512):
        if hash_algorithm not in zonocrypt.hashes:
            raise TypeError('Unsupported hash algorithm')
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

    def generate_certicate(self, length='RAND_LENGTH', start=12):
        chars = [
            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c',
            'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p',
            'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', 'A', 'B', 'C',
            'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P',
            'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', '!', '"', '#',
            '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', ':', ';',
            '<', '=', '>', '?', '@', '[', ']', '^', '_', '`', '{', '|', '}',
            '~', '\"', '\''
        ]
        fin = ''
        if length == 'RAND_LENGTH':
            for i in range(randint(12, 24)):
                for i in range(randint(1, 6)):
                    fin = f'{fin}{choice(chars)}'
                fin = f'{fin}/'
            return fin
        elif isinstance(length, int):
            for i in range(start, length):
                for i in range(randint(1, 6)):
                    fin = f'{fin}{choice(chars)}'
                fin = f'{fin}/'
            return fin
        else:
            raise TypeError('Expected int or cls.RAND_LENGTH')

    def encrypt_bytes(self, entity, key):
        f = Fernet(key)
        encrypted = f.encrypt(entity)
        return encrypted

    def decrypt(self, encrypted, key):
        f = Fernet(key)
        decrypted = f.decrypt(encrypted)

        return decrypted.decode('utf-8')

    def str_to_valid_key(self, ref):
        salt = 'salty'.encode()
        password = ref.encode()

        kdf = PBKDF2HMAC(algorithm=self.hash_algorithm(),
                         length=32,
                         salt=salt,
                         iterations=100000,
                         backend=default_backend())
        key = base64.urlsafe_b64encode(kdf.derive(password))

        return key

    def decrypt_raw(self, encrypted, key):
        f = Fernet(key)
        try:
            decrypted = f.decrypt(encrypted)
        except cryptography.fernet.InvalidToken:
            raise IncorrectDecryptionKey('Incorrect Decryption key')
        return decrypted

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

    def hashing_function(self, ref,iterations=100000,length=32,valid_key=True,salt=b'salt'):
        password_provided = ref
        password = password_provided.encode()
        kdf = PBKDF2HMAC(algorithm=self.hash_algorithm(),
                         length=length,
                         salt=salt,
                         iterations=iterations,
                         backend=default_backend())

        if valid_key:
            return base64.urlsafe_b64encode(kdf.derive(password))
        else:
            return kdf.derive(password)

    def gen_key(self):
        return self.__gen_key__(secrets.token_urlsafe())

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
        return int.from_bytes(byte, 'big')

    def shuffle(self, string):
        string = list(string)
        shuffle(string)
        return ''.join(string)
