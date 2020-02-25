import socket
import threading as thread
import datetime
from functools import partial

# Server Calls
HOST_CONNECT = 'HOST_CONNECT'.encode('UTF-8')
GAME_START = 'GAME_START'.encode('UTF-8')
SHUTDOWN = 'SHUTDOWN'.encode('UTF-8')
GAME_OVER = 'GAME_OVER'.encode('UTF-8')
CLIENT_CONNECT = 'FIRST_CONNECTION'.encode('UTF-8')
CONNECT_SUCCESS = 'CONNECT_SUCCESS'.encode('UTF-8')
CONNECT_FAIL = 'CONNECT_FAIL'.encode('UTF-8')
IDLE = 'IDLE'.encode('UTF-8')
WINNER = 'WINNER'.encode('UTF-8')
LOSER = 'LOSER'.encode('UTF-8')


class Server:
    def __init__(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.port = 5557
        self.ip = '127.0.0.1'
        self.shutdown_signal = False
        self.gameover_signal = False

        self.connected_clients = []
        self.client_threads = []

    def mainLoop(self):
        while not self.shutdown_signal:
            try:
                client_data, client_addr = self.checkForResponse()
                self.checkClient(client_addr)

                self.interpretCall(client_data, client_addr)
            except OSError:
                self.shutdown()
                break;

    def checkForResponse(self):
        client_data, client_addr = self.server.recvfrom(1024)
        return client_data, client_addr

    def checkClient(self, client_addr):
        if client_addr not in self.connected_clients:
            self.connected_clients.append(ClientData(client_addr))

    def interpretCall(self, server_call, client_addr):
        if server_call == CLIENT_CONNECT:
            self.server.sendto(CONNECT_SUCCESS, client_addr)
        elif server_call == GAME_START:
            self.broadcast(GAME_START)
        elif server_call == IDLE:
            pass
            # self.server.sendto(IDLE, client_addr)

    def broadcast(self, server_call):
        for client in self.connected_clients:
            self.server.sendto(server_call, client.address)

    def getHostInfo(self):
        try:
            host_name = socket.gethostname()
            self.ip = socket.gethostbyname(host_name)
            return host_name, self.ip, self.port
        except socket.error:
            print("Unable to get Hostname and/or IP Address")

    def serverSetup(self, ip_address, port):
        if ip_address is not None and port is not None:
            self.ip = ip_address
            self.port = port
            self.server.bind((ip_address, port))
        else:
            self.server.bind((self.ip, self.port))

        self.mainLoop()

    def closeThreads(self):
        for th in self.client_threads:
            th.join()

    def shutdown(self):
        self.shutdown_signal = True
        self.closeThreads()
        self.server.close()


class ClientData:
    def __init__(self, address, nickname=None):
        self.address = address
        self.name = nickname

        self.score = 0.0
        self.isWinner = False


def prepData(data):
    data.decode('UTF-8')
    data = repr(data)[2:-1]
    data.strip()

    return data


def doubler(num):
    return num * num


if __name__ == '__main__':
    game_server = Server()
    host_name, server_ip, port_number = game_server.getHostInfo()

    print('Starting solo server operation...\nServer info: {}:{}'.format(server_ip, port_number))
    game_server.serverSetup(server_ip, port_number)
