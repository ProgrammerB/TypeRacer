"""
Developers: Braxton Laster, Ben Rader
Desc: Server side of UDP example, handles syncing clients together
"""

import socket
import random

# Server Calls
HOST_CONNECT = 'HOST_CONNECT'
GAME_START = 'GAME_START'
GAME_OVER = 'GAME_OVER'
CLIENT_CONNECT = 'FIRST_CONNECTION'
CONNECT_SUCCESS = 'CONNECT_SUCCESS'
IDLE = 'IDLE'
WINNER = 'WINNER'
RECEIVE_GAME_OVER = 'REC_GAME_OVER'
UNKNOWN_STATUS = 'UNKNOWN STATUS'


class Server:
    """Entire backend of typeRacer, syncs connected clients, determines winners, checks for client input continuously"""
    def __init__(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.port = 5557
        self.ip = '127.0.0.1'
        self.shutdown_signal = False

        self.connected_clients = []

    def mainLoop(self):
        """Continuously checks for input from client

        In a singular loop, if it has a response will check who sent it, add them to connected_clients[] if not found,
        and calls interpretCall() to act on the data the client sent
        """
        while not self.shutdown_signal:
            try:
                self.server.settimeout(0.5)
                client_data, client_addr = self.server.recvfrom(1024)

                self.checkClient(client_addr)

                self.interpretCall(client_data.decode('UTF-8'), client_addr)
                if self.checkGameOver():
                    break
            except OSError:
                self.shutdown()
                break

    def checkClient(self, client_addr):
        """Takes address of client, checks it against the connected_clients, adds to list if not found"""
        if client_addr not in [client.address for client in self.connected_clients]:
            self.connected_clients.append(ClientData(client_addr))

    def interpretCall(self, server_call, client_addr):
        """Responds to client(s) depending on the server_call sent"""
        if '|' in server_call:
            server_call, data = server_call.split('|', 1)

        if server_call == CLIENT_CONNECT:
            self.server.sendto(CONNECT_SUCCESS.encode('UTF-8'), client_addr)

        elif server_call == GAME_START:
            self.broadcast(GAME_START + '|' + self.randomSentence('bee_movie_script.txt'))

        elif server_call == GAME_OVER:
            self.updateClient(client_addr, data, is_finished=True)
            self.server.sendto(GAME_OVER.encode('UTF-8'), client_addr)

        elif server_call == RECEIVE_GAME_OVER:
            client = self.findClient(client_addr)
            client.rec_game_over = True

        elif server_call == IDLE:
            self.server.sendto(IDLE.encode('UTF-8'), client_addr)

    def checkGameOver(self):
        """Tells if all clients confirmed they received the GAME_OVER call

        If True, then send WINNER flag w/ the winning clients IP attached to all connected clients
        :returns True or False
        """
        if all(client.rec_game_over for client in self.connected_clients):
            self.broadcast(WINNER + '|' + str(self.checkWinner()))
            return True
        else:
            return False

    def broadcast(self, server_call):
        """Sends something to all clients in connected_clients[]

        server_call: Text to send
        """
        for client in self.connected_clients:
            self.server.sendto(server_call.encode('UTF-8'), client.address)

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

    def shutdown(self):
        self.shutdown_signal = True
        self.server.close()

    def checkWinner(self):
        winner = [high_score for high_score in self.connected_clients if high_score.score == max(client.score for client in self.connected_clients)]
        winner[0].is_winner = True
        return winner[0].address[0]

    def randomSentence(self, fname):
        lines = open(fname).read().splitlines()
        return random.choice(lines)

    def updateClient(self, client_addr, score, is_finished):
        client = self.findClient(client_addr) if self.findClient(client_addr) else print('Client {} not found'.format(client_addr))
        client.score = score
        client.is_inished = is_finished

    def findClient(self, client_addr):
        for client in self.connected_clients:
            if client_addr == client.address:
                return client
        else:
            return False


class ClientData:
    """Class to store all data from a singular client in 1 place"""
    def __init__(self, address):
        self.address = address

        self.score = 0.0
        self.is_winner = False
        self.is_finished = False
        self.rec_game_over = False


if __name__ == '__main__':
    game_server = Server()
    host_name, server_ip, port_number = game_server.getHostInfo()

    print('Starting solo server operation...\nServer info: {}:{}'.format(server_ip, port_number))
    game_server.serverSetup(server_ip, port_number)
