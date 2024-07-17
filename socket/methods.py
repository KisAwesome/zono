from .exceptions import *
import zono.zonocrypt
import socket
import errno


show_full_error = False


def wrap_error(e):
    if zono.socket.show_full_error:
        return e


objcrypt = zono.zonocrypt.zonocrypt()


def _recv(conn, buffer):
    try:
        return conn.recv(buffer)

    except socket.timeout as e:
        raise ReceiveError(2) from wrap_error(e)

    except ConnectionResetError as e:
        raise ReceiveError(5) from wrap_error(e)
    except OSError as err:
        if err.errno == errno.EBADF:
            raise ReceiveError(4) from wrap_error(err)

        raise err


def _send(conn, data):
    try:
        conn.sendall(data)
    except socket.timeout as e:
        raise SendError(2) from wrap_error(e)
    except BrokenPipeError as e:
        raise SendError(6) from wrap_error(e)
    except ConnectionAbortedError as e:
        raise SendError(13) from wrap_error(e)
    except OSError as err:
        if err.errno == errno.EBADF:
            raise SendError(4) from wrap_error(err)
        raise err
    return 0


def recv(conn, buffer, timeout, session_key, _format):
    try:
        conn.settimeout(timeout)
    except OSError as err:
        if err.errno == errno.EBADF:
            raise ReceiveError(14) from wrap_error(err)
    try:
        pck = _recv(conn, buffer).decode(_format)
        if len(pck) == 0:
            raise ReceiveError(12)
        msg_len = int(pck)
    except ValueError as e:
        print(pck)
        raise ReceiveError(1) from wrap_error(e)

    msg = _recv(conn, msg_len)

    try:
        obj = objcrypt.decrypt(msg, session_key)
    except zono.zonocrypt.IncorrectDecryptionKey as e:
        raise ReceiveError(3) from wrap_error(e)
    return obj


def send(conn, pkt, session_key, _format, buffer):
    message = objcrypt.encrypt(pkt, session_key)
    msg_length = len(message)
    send_length = str(msg_length).encode(_format)
    send_length += b" " * (buffer - len(send_length))

    _send(conn, send_length)
    _send(conn, message)
    return 0


def send_raw(conn, pkt, _format, buffer):
    message = objcrypt.encode(pkt)
    msg_length = len(message)

    send_length = str(msg_length).encode(_format)
    send_length += b" " * (buffer - len(send_length))

    _send(conn, send_length)
    _send(conn, message)
    return 0


def recv_raw(conn, buffer, _format, timeout, decode=True):
    conn.settimeout(timeout)
    try:
        msg_len = int(_recv(conn, buffer).decode(_format))
    except ValueError as e:
        raise ReceiveError(1) from wrap_error(e)
    msg = _recv(conn, msg_len)
    if decode:
        msg = objcrypt.decode(msg)
    return msg
