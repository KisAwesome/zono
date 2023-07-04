import cryptography.hazmat.primitives.asymmetric.padding
import cryptography.hazmat.primitives.asymmetric.rsa
import cryptography.hazmat.primitives.serialization
import zono.socket
import zono.zonocrypt
import zono.workers
import zono.events
import threading
import secrets
import socket
import errno
import copy

Crypt = zono.zonocrypt.zonocrypt()


class SecureSocket:
    def __init__(self):
        self.buffer = 512
        self.format = "utf-8"
        zono.events.attach(self, always_event_group=True)
        self.register_event("client_info", lambda: {})
        self.register_event("on_connect", lambda: None)
        self.server_info = None

    
    def wrap_event(self, event,*args,**kwargs):
        ret = self.run_event(event,*args,**kwargs)

        n = dict()
        for i in ret:
            n|=i
        return n


    def connection_status(self):
        return self.socket.getsockopt(socket.SOL_SOCKET,socket.SO_ERROR) == 0 
        # try:
        #     data = self.socket.recv(1)
        #     if data == b'':
        #         return True
        #     else:
        #         return False
        # except ConnectionResetError:
        #     return False
        # except socket.error as e:
        #     if e.errno == errno.EWOULDBLOCK or e.errno == errno.EAGAIN or e.errno == errno.EBADF:
        #         return False
        #     else:
        #         raise

    
    def connect(self,addr):
        try:
            self._connect(addr)
        except zono.socket.ReceiveError as e:
            if e.errorno == 3:
                raise zono.socket.ConnectionFailed(8)
            raise zono.socket.ConnectionFailed(10)
        except zono.socket.SendError as e:
            raise zono.socket.ConnectionFailed(10)
    def _connect(self, addr):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect(addr)

        except ConnectionRefusedError:
            raise zono.socket.ConnectionFailed(7)
        num1 = secrets.token_bytes(32)
        try:
            self.send_raw(dict(num=num1))
            pkt = self.recv_raw()
        except zono.socket.ReceiveError:
            raise zono.socket.ConnectionFailed(9)
        except zono.socket.SendError:
            raise zono.socket.ConnectionFailed(9)
        num2 = pkt["kdn"]
        _pem = pkt["pem"]
        public_key = cryptography.hazmat.primitives.serialization.load_pem_public_key(
            _pem
        )

        num3 = secrets.token_bytes(32)

        num3_enc = public_key.encrypt(
            num3,
            cryptography.hazmat.primitives.asymmetric.padding.OAEP(
                mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                    algorithm=cryptography.hazmat.primitives.hashes.SHA384()
                ),
                algorithm=cryptography.hazmat.primitives.hashes.SHA384(),
                label=None,
            ),
        )
        self.send_raw(dict(num=num3_enc))

        key_deriv = num1 + num2 + num3
        self.session_key = Crypt.hashing_function(key_deriv)

        self.send(self.wrap_event("client_info"))
        status = self.recv()
        self.buffer = status.get("buffer", self.buffer)
        if status.get("event_socket", False):
            _ev = copy.copy(self.event_manager)
            self.event_socket = EventSocket()
            _ev.attached_to = None
            _ev.attach(self.event_socket)
            self.event_socket._connect(addr)
            self.event_socket.send(
                dict(
                    path="_event_socket",
                    addr=tuple(self.socket.getsockname()),
                    key=self.session_key,
                )
            )
            res = self.event_socket.recv()
            if res["success"]:
                self.event_thread = threading.Thread(target=self.event_listiner_)
                self.event_thread.start()
                self.event_socket.interval = zono.workers.set_interval(self.event_socket.status['timeout']-5,self.event_socket.keep_alive)
            else:
                raise Exception("Failed to start event listener")

        self.interval = zono.workers.set_interval(status['timeout']*0.85,self.keep_alive)
        self.server_info = status
        self.run_event("on_connect")



    def keep_alive(self):
        return self.send(dict(
            _keepalive=True,
            path=None
        ))

    def event_listiner_(self):
        while True:
            try:
                ev = self.event_socket.recv()
                self.run_event("socket_event", ev)
            except zono.socket.ReceiveError as e:
                e.alive=True
                try:
                    self.keep_alive()
                    self.event_socket.keep_alive()
                except zono.socket.SendError:
                    e.alive=False
                return self.run_event("event_listiner_error", e)
            except BaseException as e:
                self.run_event("event_listiner_error", e)

    def send(self, pkt,buffer=None):
        buffer = buffer or self.buffer 
        return zono.socket.send(self.socket,pkt,self.session_key,self.format,buffer)


    def recv(self, buffer=None,timeout=None):
        buffer = buffer or self.buffer
        return zono.socket.recv(self.socket,buffer,timeout,self.session_key,self.format)
    
    def request(self, path, pkt=dict(), _recv=True,buffer=None,timeout=None):
        pkt["path"] = path
        self.send(pkt)
        if _recv:
            return self.recv(buffer=buffer,timeout=timeout)

    def send_raw(self, pkt):
        return zono.socket.send_raw(self.socket,pkt,self.format,self.buffer)

    def recv_raw(self,timeout=None):
        return zono.socket.recv_raw(self.socket,self.buffer,self.format,timeout)

    def close(self):
        self.socket.close()
        zono.workers.cancel_interval(self.interval)
        if hasattr(self, "event_socket"):
            self.event_socket.close()
            self.event_thread.join()


class EventSocket(SecureSocket):
    def _connect(self, addr):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.socket.connect(addr)

        except ConnectionRefusedError:
            raise zono.socket.ConnectionFailed(7)
        num1 = secrets.token_bytes(32)
        try:
            self.send_raw(dict(num=num1))
            pkt = self.recv_raw()
        except zono.socket.ReceiveError:
            raise zono.socket.ConnectionFailed(9)
        except zono.socket.SendError:
            raise zono.socket.ConnectionFailed(9)
        num2 = pkt["kdn"]
        _pem = pkt["pem"]
        public_key = cryptography.hazmat.primitives.serialization.load_pem_public_key(
            _pem
        )

        num3 = secrets.token_bytes(32)

        num3_enc = public_key.encrypt(
            num3,
            cryptography.hazmat.primitives.asymmetric.padding.OAEP(
                mgf=cryptography.hazmat.primitives.asymmetric.padding.MGF1(
                    algorithm=cryptography.hazmat.primitives.hashes.SHA384()
                ),
                algorithm=cryptography.hazmat.primitives.hashes.SHA384(),
                label=None,
            ),
        )
        self.send_raw(dict(num=num3_enc))

        key_deriv = num1 + num2 + num3
        self.session_key = Crypt.hashing_function(key_deriv)

        self.send(self.run_event("client_info"))

        self.status = self.recv(buffer=512)
        self.buffer = self.status.get("buffer", self.buffer)