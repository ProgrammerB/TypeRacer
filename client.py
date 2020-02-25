import socket
import sys
import tkinter as tk
from tkinter import ttk
import server
import threading as thread
import time
from difflib import SequenceMatcher

# Style information used through windows
MAIN_TEXT_FONT = ('Verdana', 11)
MAIN_TITLE_FONT = ('Verdana', 18)

# Various Flags used to trigger functions
HOST = 'HOST'
CLIENT = 'CLIENT'
GAME_RUNNING = 'GAME_RUNNING'
SHUTDOWN = 'SHUTDOWN'
TIMER_RUNNING = 'TIMER_RUNNING'
RECENT_CONNECTION = 'RECENT_CONNECTION'
WINNER = 'WINNER'

# Game-related dict references
FINISH_TIME = 'FINISH_TIME'
ACCURACY = 'ACCURACY'
SCORE = 'SCORE'
USER_INPUT = 'USER'
SERVER_INPUT = 'SERVER'


class TypeRacer(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.protocol('WM_DELETE_WINDOW', self.onClosing)
        self.server = server.Server()
        self.server_thread = thread.Thread()
        self.listener_thread = thread.Thread()

        self.host_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.flags = {}
        for flag in [HOST, CLIENT, GAME_RUNNING, SHUTDOWN, TIMER_RUNNING, RECENT_CONNECTION, WINNER]:
            self.flags[flag] = False

        self.player_stats = {
            FINISH_TIME: 0.0,
            ACCURACY: 0.0,
            SCORE: 0.0,
            USER_INPUT: 'None',
            SERVER_INPUT: 'None'
        }

        self.title('TypeRacer')
        self.resizable(False, False)

        container = tk.Frame(self)
        container.pack(side='top', fill='both', expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frame_list = [MainMenu, JoinGame, HostGame, Help, GameScreen, PostGame]
        self.frames = {}

        for frame in self.frame_list:
            current_frame = frame(container, self)
            self.frames[frame] = current_frame
            current_frame.grid(row=0, column=0, sticky='nsew')

        self.showFrame(MainMenu)

    def showFrame(self, requested_frame):
        frame = self.frames[requested_frame]
        frame.tkraise()

    def runServer(self, server_info):
        self.flags[HOST] = True
        self.server_thread = thread.Thread(target=self.server.serverSetup,
                                           args=server_info).start()
        self.listener_thread = thread.Thread(target=self.serverListener,
                                             args=server_info).start()

    def clientSetup(self, server_info):
        if self.flags[HOST]:
            server_call = server.GAME_START
        elif self.flags[CLIENT]:
            server_call = server.CLIENT_CONNECT
        else:
            server_call = server.IDLE

        self.host_server.sendto(server_call.encode('UTF-8'), server_info)
        self.showFrame(GameScreen)

    def serverListener(self, ip, port):
        while not self.flags[SHUTDOWN]:
            try:
                if self.flags[RECENT_CONNECTION]:
                    self.flags[RECENT_CONNECTION] = False

                    self.server.server.settimeout(5)
                    server_call, ip_addr = self.host_server.recvfrom(1024)
                    self.interpretServer(server_call.decode('UTF-8'))
                else:
                    self.host_server.sendto(server.IDLE.encode('UTF-8'), (ip, port))
                    self.flags[RECENT_CONNECTION] = True
            except socket.error:
                pass

    def interpretServer(self, server_call):
        if '|' in server_call:
            server_call, data = server_call.split('|', 1)

        if server_call == server.GAME_START:
            self.flags[GAME_RUNNING] = True
            self.player_stats[SERVER_INPUT] = data
            self.frames[GameScreen].text_to_type.configure(text=self.player_stats[SERVER_INPUT])

            if not self.flags[TIMER_RUNNING]:
                self.flags[TIMER_RUNNING] = True
                self.frames[GameScreen].runTimerThread()

    # Deals with making sure everything closes properly when closing the window
    def onClosing(self):
        try:
            self.flags[SHUTDOWN] = True
            self.flags[GAME_RUNNING] = False
            self.flags[TIMER_RUNNING] = False

            self.destroy()
            self.server.shutdown()
        except:
            sys.exit(0)


class MainMenu(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        host_name, ip, port = controller.server.getHostInfo()

        MainMenu.config(self, bg="black")
        label = tk.Label(self, bg="black", fg="#abb0b4", text="Type Racer", font=("Verdana", 48))
        label.pack(pady=10, padx=10)

        join_button = ttk.Button(self, text="Join Game", command=lambda: controller.showFrame(JoinGame))
        join_button.place(height=40, width=300, relx=0.50, rely=0.35, anchor=tk.CENTER)

        host_button = ttk.Button(self, text="Host Game",
                                 command=lambda: [controller.showFrame(HostGame), controller.runServer((ip, port))])
        host_button.place(height=40, width=300, relx=0.50, rely=0.50, anchor=tk.CENTER)

        help_button = ttk.Button(self, text="Help", command=lambda: controller.showFrame(Help))
        help_button.place(height=40, width=300, relx=0.50, rely=0.65, anchor=tk.CENTER)


class JoinGame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        help_text = tk.Text(self, bd=1, bg='white smoke', fg='black',
                            height=2, width=40,
                            wrap=tk.WORD, padx=5, pady=5)

        help_text.tag_configure('center', justify='center')
        help_text.tag_add('center', 1.0, 'end')
        help_text.insert(tk.INSERT, 'To join a game please enter the IP address of the host in the space below')
        help_text.place(relx=0.5, rely=0.35, anchor=tk.CENTER)

        ip_label = tk.Label(self,
                            text='Enter IP Address',
                            font=MAIN_TITLE_FONT)
        ip_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        address_entry = ttk.Entry(self)
        address_entry.place(relx=0.5, rely=0.65, anchor=tk.CENTER)

        connect_button = ttk.Button(self,
                                    text='Connect',
                                    command=lambda: self.startGameAsClient(address_entry.get()))
        connect_button.place(relx=0.5, rely=0.75, anchor=tk.CENTER)

        return_button = ttk.Button(self,
                                   text='Main Menu',
                                   command=lambda: controller.showFrame(MainMenu))
        return_button.place(relx=0.50, rely=0.9, anchor=tk.CENTER)

    def startGameAsClient(self, raw_server_info):
        ip, port = raw_server_info.split(':', 1)
        self.controller.client_flag = True
        self.controller.clientSetup((ip, int(port)))
        self.controller.listener_thread = thread.Thread(target=self.controller.serverListener,
                                                        args=(ip, int(port))).start()


class HostGame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        host_name, server_ip, port_number = controller.server.getHostInfo()

        title = tk.Label(self,
                         text='Host Setup',
                         font=MAIN_TITLE_FONT)
        title.place(relx=0.5, rely=0.1, anchor=tk.CENTER)

        help_text = tk.Text(self, bd=1, bg='white smoke', fg='black',
                            height=7, width=40,
                            wrap=tk.WORD, padx=5, pady=5)
        help_text.insert(tk.INSERT, 'To host a game please give out the ip and port listed below to other '
                                    'players. Click \'Start\' when all players connected\n\n'
                                    'Computer Name : {}\n'
                                    'IP Address    : {}\n'
                                    'Port          : {}'.format(host_name, server_ip, port_number))

        help_text.place(relx=0.5, rely=0.45, anchor=tk.CENTER)
        help_text.configure(state='disable')

        start_button = ttk.Button(self,
                                  text='Start',
                                  command=lambda: self.controller.clientSetup((server_ip, port_number)))
        start_button.place(relx=0.5, rely=0.8, anchor=tk.CENTER)

        return_button = ttk.Button(self,
                                   text='Main Menu',
                                   command=lambda: controller.showFrame(MainMenu))
        return_button.place(relx=0.50, rely=0.9, anchor=tk.CENTER)


class Help(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        text = tk.Text(self, font=("Verdana", 11))
        text.insert(tk.INSERT, '                                                     How To Play \'TypeRacer\'                         \n'
                               '_______________________________________________________________________                                \n'
                               '                                                                HOST                                   \n'
                               '1. Press "Host Game" on the Main Menu                                             \n'
                               '2. Give the displayed IP and port number                                          \n'
                               '3. When all players have connected hit start, and type                            \n'
                               '------------------------------------------------------------------------------------------------------\n'
                               '                                                                Client                                \n'
                               '1. Press "Join Game" on the Main Menu                                             \n'
                               '2. Get the IP number and port number from the Host                                \n'
                               '      -type it in in format [IP #]:[port #]                                       \n'
                               '3. Once the host starts the game, a sentence will popup with the text box below it\n'
                               '4. Once done typing, HIT ENTER                                                    \n'
                               '5. Once all players are finished, score is determined by accuracy and time to     \n'
                               '   answer accuracy and time to answer.  Winner is then displayed   along with all \n'
                               '   of your stats                                                                  \n'
                               '_______________________________________________________________________\n'
                                )
        text.configure(state='disable')
        text.pack()

        temp_button = ttk.Button(self,
                                 text='Main Menu',
                                 command=lambda: controller.showFrame(MainMenu))
        temp_button.place(relx=0.50, rely=0.9, anchor=tk.CENTER)


class GameScreen(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        self.timer = '0.00s'
        self.tic = 0.00
        self.finish_time = 0.00
        self.stop_threads = False
        # self.user_input = ""
        # self.score = 0
        # self.accuracy = 0

        self.temp_button = ttk.Button(self, text="Main Menu", command=lambda: controller.showFrame(MainMenu))
        self.temp_button.place(relx=0.50, rely=0.5, anchor=tk.CENTER)

        self.time_display = tk.Label(self, text='0.00s'.format(self.timer))
        self.time_display.place(relx=.50, rely=.10, anchor=tk.CENTER)
        self.timer_thread = thread.Thread(target=self.runTimer)

        self.text_to_type = tk.Label(self, text=self.controller.player_stats[SERVER_INPUT])
        self.text_to_type.place(relx=.50, rely=.30, anchor=tk.CENTER)

        self.typing_box = tk.Text(self)
        self.typing_box.place(height=50, width=400, relx=.50, rely=.75, anchor=tk.CENTER)

        self.typing_box.bind('<Return>', self.onEnterPressed, self.retrieve_input)

    def runTimerThread(self):
        self.timer_thread.start()
        self.tic = time.time()

    def runTimer(self):
        while self.controller.flags[TIMER_RUNNING]:
            self.time_display.configure(text='{:.2f}s'.format(time.time() - self.tic))
            self.update()
            time.sleep(.025)

    def retrieve_input(self, event=None):
        user_input = self.typing_box.get('1.0', 'end-1c')
        user_input.strip('\n')
        return user_input

    def getScore(self, a, b):
        similarity_metric = SequenceMatcher(lambda x: x == ' ', a, b).ratio()
        self.controller.player_stats[ACCURACY] = similarity_metric
        score = ((similarity_metric * 1) ** 4 / (self.controller.player_stats[FINISH_TIME])) * 1000
        if similarity_metric is 1.0:
            score = ((similarity_metric * 1.5) ** 4 / (self.controller.player_stats[FINISH_TIME])) * 1000
        print('{} is the similarity metric'.format(similarity_metric))
        return score

    def onEnterPressed(self, event=None):
        self.controller.flags[TIMER_RUNNING] = False
        toc = time.time()
        self.controller.player_stats[FINISH_TIME] = toc - self.tic
        self.controller.player_stats[USER_INPUT] = self.retrieve_input(self)
        self.controller.player_stats[SCORE] = self.getScore(self.controller.player_stats[USER_INPUT],
                                                            self.controller.player_stats[SERVER_INPUT])
        print(self.controller.player_stats[SCORE])

        self.controller.host_server.sendto((server.GAME_OVER + '|' +
                                            '{:.3f}'.format(self.controller.player_stats[SCORE])).encode('UTF-8'),
                                           (self.controller.server.ip, self.controller.server.port))

        self.controller.frames[PostGame].updateText()
        self.controller.showFrame(PostGame)


class PostGame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        computer_name, ip_addr, port_number = controller.server.getHostInfo()
        print(controller.player_stats[FINISH_TIME])

        self.winner_ip = '10.20.0.161'  # TEST CODE: TO BE USED WITH IP FROM SERVER MSG
        print(ip_addr)
        if self.winner_ip == ip_addr:
            final_result = tk.Label(self, text='VICTORY', font=('Verdana', 48))
            final_result.place(relx=0.5, rely=0.35, anchor=tk.CENTER)
            label = tk.Label(self, text='You won the game'.format(self.winner_ip), font=('Verdana', 18))
            label.pack(pady=10, padx=10)
        else:
            final_result = tk.Label(self, text='LOSS', font=('Verdana', 48))
            final_result.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
            label = tk.Label(self, text="{} won the game".format(self.winner_ip), font=('Verdana', 18))
            label.pack(pady=10, padx=10)

        self.user_stats = tk.Text(self, bd=1, bg='white smoke', fg='black',
                                  height=7, width=60, wrap=tk.WORD, padx=5, pady=5)
        self.user_stats.insert(tk.INSERT, '                      :YOUR STATS:                   \n\n'
                                          'Time to answer : {:.4f} seconds\n'
                                          'Score          : {:.3f} points\n'
                                          'Accuracy       : {:.4f}%\n'
                                          'Your Sentence  : {}\n'
                                          'Server Sentence: {}'
                               .format(self.controller.player_stats[FINISH_TIME], self.controller.player_stats[SCORE],
                                       self.controller.player_stats[ACCURACY] * 100,
                                       self.controller.player_stats[USER_INPUT],
                                       self.controller.player_stats[SERVER_INPUT]))

        self.user_stats.place(relx=0.5, rely=0.75, anchor=tk.CENTER)

    def updateText(self):
        self.user_stats.configure(state='normal')
        self.user_stats.delete('1.0', 'end')
        self.user_stats.insert(tk.INSERT, '                      :YOUR STATS:                   \n\n'
                                          'Time to answer : {:.4f} seconds\n'
                                          'Score          : {:.3f} points\n'
                                          'Accuracy       : {:.4f}%\n'
                                          'Your Sentence  : {}\n'
                                          'Server Sentence: {}'
                               .format(self.controller.player_stats[FINISH_TIME], self.controller.player_stats[SCORE],
                                       self.controller.player_stats[ACCURACY] * 100,
                                       self.controller.player_stats[USER_INPUT],
                                       self.controller.player_stats[SERVER_INPUT]))
        self.user_stats.configure(state='disable')


if __name__ == '__main__':
    game = TypeRacer()
    game.geometry('720x360')
    game.mainloop()
