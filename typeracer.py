"""
Developers: Braxton Laster, Ben Rader
Desc: Example of UDP between 2 computers via a GUI typing game
"""

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
    """Bases class that manages important client functions and server interactions with the client

    In the frame classes [MainMenu, JoinGame, HostGame, etc...] TypeRacer can be referenced via [controller] variable in
    their respective classes

    Used Resources
    --------------
    https://pythonprogramming.net/object-oriented-programming-crash-course-tkinter/?completed=/tkinter-depth-tutorial-making-actual-program/
    - Used this to get the basic idea of using tkinter in terms of classes
    """

    def __init__(self):
        tk.Tk.__init__(self)
        self.protocol('WM_DELETE_WINDOW', self.onClosing)
        self.server = server.Server()
        self.server_thread = thread.Thread()
        self.listener_thread = thread.Thread()

        self.client_ip = socket.gethostbyname(socket.gethostname())
        self.host_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.connect_ip = '127.0.0.1'
        self.connect_port = 5557

        self.flags = {}
        for flag in [HOST, CLIENT, GAME_RUNNING, SHUTDOWN, TIMER_RUNNING, RECENT_CONNECTION, WINNER]:
            self.flags[flag] = False

        self.player_stats = {
            FINISH_TIME: 0.0,
            ACCURACY: 0.0,
            SCORE: 0.0,
            USER_INPUT: 'None',
            SERVER_INPUT: 'GET READY'
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
        """Takes in a frame class and raises it to the front of the GUI"""
        frame = self.frames[requested_frame]
        frame.tkraise()

    def runServer(self, server_info):
        """Starts 2 server-related threads and tells client it's the host device

        self.server_thread: Starts running the game server that clients connect to
        self.listener_thread: Starts listening for server input to interpret
        """
        self.flags[HOST] = True
        self.server_thread = thread.Thread(target=self.server.serverSetup,
                                           args=server_info).start()
        self.listener_thread = thread.Thread(target=self.serverListener,
                                             args=server_info).start()

    def clientSetup(self, server_info):
        """Sends initial connect msg to server and moves the actual gameplay screen to the front

        If client is on same device as server then send a GAME_START signal to the server, otherwise tell the server
        it is a client. This is because clientSetup() is called at different points depending on if the client has the
        same ip with the server host.
        """
        if self.flags[HOST]:
            server_call = server.GAME_START
        elif self.flags[CLIENT]:
            server_call = server.CLIENT_CONNECT
        else:
            server_call = server.UNKNOWN_STATUS

        self.host_server.sendto(server_call.encode('UTF-8'), server_info)
        self.showFrame(GameScreen)

    def serverListener(self, ip, port):
        while not self.flags[SHUTDOWN]:
            try:
                if self.flags[RECENT_CONNECTION]:
                    self.flags[RECENT_CONNECTION] = False

                    self.host_server.settimeout(0.5)
                    server_call, ip_addr = self.host_server.recvfrom(1024)
                    self.interpretServer(server_call.decode('UTF-8'), ip, port)
                else:
                    self.host_server.sendto(server.IDLE.encode('UTF-8'), (ip, port))
                    self.flags[RECENT_CONNECTION] = True
            except socket.error:
                pass

    def interpretServer(self, server_call, ip, port):
        if '|' in server_call:
            server_call, data = server_call.split('|', 1)

        # if server_sends msg ("GAME_START") then do this
        if server_call == server.GAME_START:
            self.flags[GAME_RUNNING] = True
            self.player_stats[SERVER_INPUT] = data if data else 'Error retrieving text'
            self.frames[GameScreen].text_to_type.configure(text=self.player_stats[SERVER_INPUT])

            # if TIMER_RUNNING flag not set to true - set to true
            if not self.flags[TIMER_RUNNING]:
                self.flags[TIMER_RUNNING] = True
                self.frames[GameScreen].runTimerThread()

        # if server sends "GAME_OVER" msg - let program know game is not running (set flag to false)
        # let server know "GAME_OVER" msg was received
        elif server_call == server.GAME_OVER:
            self.flags[GAME_RUNNING] = False
            self.host_server.sendto(server.RECEIVE_GAME_OVER.encode('UTF-8'), (ip, port))

        # if server sends message "WINNER" (you are the winner) -
        elif server_call == server.WINNER:
            print('Mine: {} Winner: {}'.format(self.client_ip, data))
            if str(self.client_ip) == data:
                self.flags[WINNER] = True
            else:
                self.frames[PostGame].winner_ip = data

            self.frames[PostGame].updateText()
            self.showFrame(PostGame)

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
    """Default window for TypeRacer class

    GUI Functionality
    -----------------
    join_button: Moves JoinGame frame to the front
    host_button: Moves HostGame frame to the front, and starts the server via controller.runServer()
    help_button: Moves HelpMenu frame to the front
    """

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        host_name, ip, port = controller.server.getHostInfo()

        # set some stylistic feautures for the Main Menu frame
        MainMenu.config(self, bg="black")
        label = tk.Label(self, bg="black", fg="#abb0b4", text="Type Racer", font=("Verdana", 48))
        label.pack(pady=10, padx=10)

        # Join Game button - brings JoinGame frame to the front
        join_button = ttk.Button(self, text="Join Game", command=lambda: controller.showFrame(JoinGame))
        join_button.place(height=40, width=300, relx=0.50, rely=0.35, anchor=tk.CENTER)

        # Host Game button - brings HostGame frame to the front
        host_button = ttk.Button(self, text="Host Game",
                                 command=lambda: [controller.showFrame(HostGame), controller.runServer((ip, port))])
        host_button.place(height=40, width=300, relx=0.50, rely=0.50, anchor=tk.CENTER)

        # Help page button - brings Help frame to the front
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
        # if the input is not empty - take input and split input into ip and port variables
        if raw_server_info:
            try:
                ip, port = raw_server_info.split(':', 1)
                self.controller.connect_ip = ip
                self.controller.connect_port = int(port)
                self.controller.client_flag = True
                self.controller.clientSetup((ip, int(port)))
                self.controller.listener_thread = thread.Thread(target=self.controller.serverListener,
                                                                args=(ip, int(port))).start()
            # if an error is thrown - either it did not connect or the split couldn't happen
            # display message to user to change input
            except:
                label = tk.Label(self,
                                 text='Could not connect - Format may be incorrect',
                                 font=('Verdana', 11),
                                 fg='red')
                label.place(relx=0.5, rely=0.57, anchor=tk.CENTER)
                self.after(4000, label.destroy)
        # if the input is empty display to the user that it is empty for 4 seconds
        else:
            label = tk.Label(self,
                             text='Nothing was entered...',
                             font=('Verdana', 11),
                             fg='red')
            label.place(relx=0.5, rely=0.57, anchor=tk.CENTER)
            self.after(4000, label.destroy)


class HostGame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        host_name, controller.connect_ip, controller.connect_port = controller.server.getHostInfo()

        title = tk.Label(self,
                         text='Host Setup',
                         font=MAIN_TITLE_FONT)
        title.place(relx=0.5, rely=0.1, anchor=tk.CENTER)

        # displays the IP of the user and the port number which will be used
        # players who hit join game will type this information into an input box
        help_text = tk.Text(self, bd=1, bg='white smoke', fg='black',
                            height=7, width=40,
                            wrap=tk.WORD, padx=5, pady=5)
        help_text.insert(tk.INSERT, 'To host a game please give out the ip and port listed below to other '
                                    'players. Click \'Start\' when all players connected\n\n'
                                    'Computer Name : {}\n'
                                    'IP Address    : {}\n'
                                    'Port          : {}'.format(host_name, controller.connect_ip,
                                                                controller.connect_port))

        help_text.place(relx=0.5, rely=0.45, anchor=tk.CENTER)
        help_text.configure(state='disable')

        start_button = ttk.Button(self,
                                  text='Start',
                                  command=lambda: self.controller.clientSetup(
                                      (controller.connect_ip, controller.connect_port)))
        start_button.place(relx=0.5, rely=0.8, anchor=tk.CENTER)

        return_button = ttk.Button(self,
                                   text='Main Menu',
                                   command=lambda: controller.showFrame(MainMenu))
        return_button.place(relx=0.50, rely=0.9, anchor=tk.CENTER)


# Help page frame that is brought to the front when 'Help' is pressed on the main menu
class Help(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        text = tk.Text(self, font=("Verdana", 11))
        text.insert(tk.INSERT,
                    '                                                     How To Play \'TypeRacer\'                         \n'
                    '_______________________________________________________________________                                \n'
                    '                                                                HOST                                   \n'
                    '1. Press "Host Game" on the Main Menu                                             \n'
                    '2. Give the displayed IP and port number                                          \n'
                    '3. When all players have connected hit start, and type                            \n'
                    '------------------------------------------------------------------------------------------------------\n'
                    '                                                               PLAYER                                 \n'
                    '1. Press "Join Game" on the Main Menu                                             \n'
                    '2. Get the IP number and port number from the Host                                \n'
                    '      -type it in in format [IP #]:[port #]                                       \n'
                    '3. Once the host starts the game, a sentence will popup with the text box below it\n'
                    '4. Once done typing, HIT ENTER                                                    \n'
                    '5. Once all players are finished, score is determined by accuracy and time to     \n'
                    '   answer.  Winner is then displayed along with all of your stats                 \n'
                    '                                                                                  \n'
                    '_______________________________________________________________________\n'
                    )
        text.configure(state='disable')
        text.pack()

        temp_button = ttk.Button(self,
                                 text='Main Menu',
                                 command=lambda: controller.showFrame(MainMenu))
        temp_button.place(relx=0.50, rely=0.9, anchor=tk.CENTER)


# frame where the game actually takes place between players and the host
# includes timer, input box, prompt, and all functions related
class GameScreen(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller  # allows for connection and more interaction with other classes
        self.waiting_msg = 'Waiting For Host to start game...'
        self.timer = '0.00'
        self.tic = 0.00
        self.finish_time = 0.00
        self.stop_threads = False

        # Button to get back to the Main Menu
        self.temp_button = ttk.Button(self, text="Main Menu", command=lambda: controller.showFrame(MainMenu))
        self.temp_button.place(relx=0.50, rely=0.5, anchor=tk.CENTER)

        # The timer display (defaulted to present waiting message before game and timer actually start updating)
        self.time_display = tk.Label(self, font=('Verdana', 20), text='{}'.format(self.waiting_msg))
        self.time_display.place(relx=.50, rely=.10, anchor=tk.CENTER)
        self.timer_thread = thread.Thread(target=self.runTimer)

        # The prompt text - takes input from SERVER_INPUT flag
        self.text_to_type = tk.Label(self, text=self.controller.player_stats[SERVER_INPUT], font=('Verdana', 11))
        self.text_to_type.place(relx=.50, rely=.30, anchor=tk.CENTER)

        # Box which player/user types the corresponding prompt in
        self.typing_box = tk.Text(self)
        self.typing_box.place(height=50, width=400, relx=.50, rely=.75, anchor=tk.CENTER)

        # When 'Enter' is pressed retrieve the input from the typing_box and run onEnterPressed function
        self.typing_box.bind('<Return>', self.onEnterPressed, self.retrieve_input)

    # when called - starts the (alreacy created) timer_thread, which allows for a running timer display w/rest of the gui
    # still being usable
    def runTimerThread(self):
        self.timer_thread.start()
        self.tic = time.time()

    # when the TIMER_RUNNING flag is caught by ServerListener and interpreted by ServerInterpreter (broadcasted by
    def runTimer(self):
        while self.controller.flags[TIMER_RUNNING]:
            self.time_display.configure(text='{:.2f}s'.format(time.time() - self.tic))
            self.update()
            time.sleep(.025)

    # used with above 'typing_box' - uses get() method to retrieve data and strip it of newline characters
    def retrieve_input(self, event=None):
        user_input = self.typing_box.get('1.0', 'end-1c')
        user_input.strip('\n')
        return user_input

    # uses Sequence Matcher from difflib library to compare 2 strings and return a metric/ratio for similarity
    def getScore(self, a, b):
        similarity_metric = SequenceMatcher(lambda x: x == ' ', a, b).ratio()
        self.controller.player_stats[ACCURACY] = similarity_metric

        # score is calculated with more weight (**4) on accuracy to prompt with time still affecting score (/finish_time *1000)
        score = ((similarity_metric * 1) ** 4 / (self.controller.player_stats[FINISH_TIME])) * 1000
        if similarity_metric is 1.0:
            score = ((similarity_metric * 1.5) ** 4 / (self.controller.player_stats[FINISH_TIME])) * 1000
        return score

    def onEnterPressed(self, event=None):
        self.controller.flags[TIMER_RUNNING] = False
        toc = time.time()
        self.controller.player_stats[FINISH_TIME] = toc - self.tic
        self.controller.player_stats[USER_INPUT] = self.retrieve_input(self)
        self.controller.player_stats[SCORE] = self.getScore(self.controller.player_stats[USER_INPUT],
                                                            self.controller.player_stats[SERVER_INPUT])

        self.controller.host_server.sendto((server.GAME_OVER + '|' +
                                            '{:.3f}'.format(self.controller.player_stats[SCORE])).encode('UTF-8'),
                                           (self.controller.connect_ip, self.controller.connect_port))


class PostGame(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller

        self.winner_ip = 'None'

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
        if self.controller.flags[WINNER]:
            self.final_result = tk.Label(self, text='VICTORY', font=('Verdana', 48))
            self.final_result.place(relx=0.5, rely=0.35, anchor=tk.CENTER)
            self.label = tk.Label(self, text='You won the game'.format(self.winner_ip), font=('Verdana', 18))
            self.label.pack(pady=10, padx=10)
        else:
            self.final_result = tk.Label(self, text='LOSS', font=('Verdana', 48))
            self.final_result.place(relx=0.5, rely=0.35, anchor=tk.CENTER)
            self.label = tk.Label(self, text="{} won the game".format(self.winner_ip), font=('Verdana', 18))
            self.label.pack(pady=10, padx=10)

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
