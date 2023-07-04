import socket
import zono.zonocrypt
from .exceptions import *
import errno

objcrypt = zono.zonocrypt.objcrypt()

def _recv(conn,buffer):
    try:
        return conn.recv(buffer)
    
    except socket.timeout:
        raise ReceiveError(2)
    
    except ConnectionResetError:
        raise ReceiveError(5)
    except OSError as err:
        if err.errno == errno.EBADF:
            raise ReceiveError(4)
        raise err


def _send(conn,data):
    try:
        conn.sendall(data)
    except socket.timeout:
        raise SendError(2)
    except BrokenPipeError:
        raise SendError(6)
    except OSError as err:
        if err.errno == errno.EBADF:
            raise SendError(4)
        raise err
    return 0

def recv(conn,buffer,timeout,session_key,_format):
    conn.settimeout(timeout)
    try:
        msg_len = int(_recv(conn,buffer).decode(_format))
    except ValueError:
        raise ReceiveError(1)
    
    msg = _recv(conn,msg_len)
    
    try:
        obj = objcrypt.decrypt(msg, session_key)
    except zono.zonocrypt.IncorrectDecryptionKey:
        raise ReceiveError(3)
    return obj


def send(conn,pkt,session_key,_format,buffer):
    message = objcrypt.encrypt(pkt, session_key)
    msg_length = len(message)
    send_length = str(msg_length).encode(_format)
    send_length += b" " * (buffer - len(send_length))

    _send(conn,send_length)
    _send(conn,message)
    return 0




def send_raw(conn,pkt,_format,buffer):
    message = objcrypt.encode(pkt)
    msg_length = len(message)

    send_length = str(msg_length).encode(_format)
    send_length += b" " * (buffer - len(send_length))

    _send(conn,send_length)
    _send(conn,message)
    return 0

def recv_raw(conn,buffer,_format,timeout):
    conn.settimeout(timeout)
    try:
        msg_len = int(_recv(conn,buffer).decode(_format))
    except ValueError:
        raise ReceiveError(1)
    msg = _recv(conn,msg_len)
    msg = objcrypt.decode(msg)
    return msg