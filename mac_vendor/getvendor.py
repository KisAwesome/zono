import os


class InvalidMacError(Exception):
    pass


class MacLookup:
    def __init__(self):
        path = f'{os.path.dirname(__file__)}/mac-vendors.txt'

        self.prefixes = {}
        with open(path, 'rb') as f:
            for l in (f.read()).splitlines():
                prefix, vendor = l.split(b":", 1)
                self.prefixes[prefix] = vendor

    def sanitise(self, _mac):
        mac = _mac.replace(":", "").replace("-", "").replace(".", "").upper()
        try:
            int(mac, 16)
        except ValueError:
            raise InvalidMacError(
                "{} contains unexpected character".format(_mac))
        if len(mac) > 12:
            raise InvalidMacError(
                "{} is not a valid MAC address (too long)".format(_mac))
        return mac

    def lookup(self, mac):
        mac = self.sanitise(mac)
        if type(mac) == str:
            mac = mac.encode("utf8")

        return self.prefixes.get(mac[:6], b'Not Found').decode("utf8")
