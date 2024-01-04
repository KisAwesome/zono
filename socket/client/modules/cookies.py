from .event_socket import SecureEventSocket
from .module_helpers import ClientModule, event
import time
import yaml
import os


def get_file(file):
    return os.path.join(os.path.dirname(__file__), file)
def form_cookies(cookies):
    if isinstance(cookies, dict):
        return cookies
    return {}

def check_cookie_file():
    file = get_file("cookies.yaml")
    if not os.path.exists(file):
        with open(file, 'w') as f:
            f.write('{}')


class Cookies(ClientModule):
    def setup(self, ctx):
        self.client = ctx.app
        self.client.save_cookies = self.save
        check_cookie_file()

    @event()
    def client_info(self, ctx):
        check_cookie_file()
        if isinstance(ctx.app, SecureEventSocket):
            return {}
        with open(get_file("cookies.yaml"), "r") as file:
            cookies = form_cookies(yaml.safe_load(file))

        server_name = self.client.server_info.get("name", "null")
        client_cookies = cookies.get(server_name, {})
        expiry = client_cookies.get("expires", None)
        if expiry is not None:
            if time.time() > expiry:
                client_cookies = {}
                cookies.pop(server_name)

                with open(get_file("cookies.yaml"), "w") as file:
                    yaml.safe_dump(cookies, file)

        return dict(cookies=client_cookies)

    @event()
    def on_connect(self, ctx):
        check_cookie_file()
        name = self.client.server_info.get("name", None)
        client_cookies = self.client.final_connect_info.get("cookies", None)
        if (name and client_cookies) is None:
            return
        self.save(name,client_cookies)


    
    
    def save(self,name=None,client_cookies=None):
        check_cookie_file()
        name = name or self.client.server_info.get("name", None)
        client_cookies = client_cookies or self.client.cookies
        if (name and client_cookies) is None:
            raise ValueError("Name and cookies need to be specified")
        
        with open(get_file("cookies.yaml"), "r") as file:
            cookies = form_cookies(yaml.safe_load(file))
        cookies[name] = client_cookies

        self.client.cookies = client_cookies
        with open(get_file("cookies.yaml"), "w") as file:
            yaml.safe_dump(cookies, file)
    
        