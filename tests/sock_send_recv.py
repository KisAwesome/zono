import zono.socket.client.modules as modules
import zono.socket.client 
import zono.colorlogger
import zono.cli 
import atexit
import sys


logger = zono.colorlogger.create_logger('socket.client',level = 1)

class App(zono.cli.Module):
    def __init__(self,client ):
        self.path = None
        self.client = client
    @zono.cli.command(description='set the path to send to')
    def path(self,ctx):
        self.path = ' '.join(ctx.args)


    @zono.cli.command(description='send message')
    def send(self,ctx):
        inp = ' '.join(ctx.args)
        if inp:
            try:
                x = eval(inp)

            except Exception as e:
                print('Eval error')
                print(f"Error: {e}")
                return
        else:
            x = dict()
        try:
            print(self.client.request(self.path,x,timeout=5))
        except zono.socket.client.ReceiveError as e:
            if e.errorno == 2:
                return print('Operation timed out')
            raise e
        except zono.socket.client.ConnectionClosed:
            logger.error('Connection closed try reconnecting')
        
    @zono.cli.command(description='connect to server')
    def reconnect(self,ctx):
        self.client.close()
        logger.info('Closed existing connection')
        addr = self.client.connection_info['addr']
        self.client = zono.socket.client.Client()
        self.client.register_event('socket_event',soc)
        self.client.load_module(modules.EventSocket())
        self.client.load_module(modules.Cookies())

        self.client.connect(addr)
        logger.info(f'Reconnected to {addr}')
        

def validate_and_parse_address(address_str):
    if address_str.lower() == "localhost":
        return "localhost", 80  # Use 7070 as default for localhost

    try:
        address, port_str = address_str.split(":")
        port = int(port_str)

        if address != "localhost":
            octets = address.split(".")
            if len(octets) == 4:
                for octet in octets:
                    if not 0 <= int(octet) <= 255:
                        return None, None

        if 1 <= port <= 65535:
            return address, port

    except (ValueError, IndexError):
        pass

    return None, None

def soc(ctx):
    print(ctx)

def close(app):
    app.client.close()
    logger.info('Closed connection to server')

def run():
    c = zono.socket.client.Client()

    c.register_event('socket_event',soc)
    c.load_module(modules.EventSocket())
    c.load_module(modules.Cookies())

    app = zono.cli.Application()

    a = App(c)


    app.default_indentation(a,lock=True)

    if len(sys.argv) == 1:
        g = input('Enter address to connect to: ')
    else:
        g = sys.argv[1]

    atexit.register(lambda: close(a._class_))
    c.connect(validate_and_parse_address(g))

    app.run()




if __name__ == '__main__':
    run()
