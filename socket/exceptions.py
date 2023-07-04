
errors = {
    1:'Error occured while recieving data length',
    2:'Operation timed out',
    3:'Data decryption error',
    4:'Bad file descriptor',
    5:"Connection has been reset by the peer",
    6:"Attempting to send through a closed connection",
    7:"Unable to connect to the server",
    8:"Error occured while exchanging secure keys with the server",
    9:'Initial handshake with the server failed',
    10:'Lost connection to the server while performing intial handshake',
}

class TransmissionError(Exception): 
    def __init__(self, errorno,raw_err=None):
        self.errorno = errorno
        self.errormsg = errors.get(errorno, "Unknown error")
        self.raw_err = raw_err
        super().__init__()

    def __str__(self):
        return f"Error {self.errorno} - {self.errormsg}"

class ReceiveError(TransmissionError):
    pass

class SendError(TransmissionError):
    pass

class ConnectionFailed(TransmissionError):
    pass