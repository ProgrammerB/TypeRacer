WHAT TYPERACER DOES:
	Tkinter GUI that uses UDP sockets to form a connection between a host and a client based on what
	the user chooses on the main menu.  Once users are connected to the host IP and the host hits
	start, the game begins.  Whoever can type the prompt in the quickest wins.  Results are displayed
	after all players have entered in their prompts.
HOW TO USE TYPERACER:

	-HOSTS AND PLAYERS MUST BE ON DIFFERENT DEVICES/IPs

	1. Download typeracer.py and server.py along with bee_movie_script.txt
		-any .txt file can be used if you search through the source code and change
		 bee_movie_script.txt to [filename].txt.  Each line in the txt can be chosen randomly
		 to be used as a prompt.
	2. Run 'typeracer.py' a terminal with Python installed or an IDE with Python
		a) Type: "python typeracer.py" as terminal command. Hit Enter.
		   (make sure you are in the right folder w/ all files in that one folder)

	3. Use the main menu to select 'Host Game' or 'Join Game'
		Host Game:
			a)Give all players the displayed IP and PORT NUMBER
				-enter/connect w/format --> [IP]:[PORT #]
			b)Once all players are connected and at the prompt screen with no prompt
			  THEN YOU MAY HIT START TO SEND PROMPTS AND START TIMERS
			c)Once all players have hit 'Enter' the server will send back the
			  winner (Best Score -- balance between time and accuracy)
		Join Game:
			a)Obtain the IP and PORT NUMBER from the host.
				-enter w/format --> [IP]:[PORT #]
			b)Press 'Connect'
				-a screen with no prompt will be displayed
				-DO NOT BEGIN UNTIL TIMER STARTS AND PROMPT CHANGES
				 This will happen once the host hits 'Start'
			c)Hit 'Enter' once you are finished typing the prompt in the text box
				-a winner should be displayed along w/your own stats when
				 everyone is finished
CONTRIBUTORS:
	Braxton Laster:
		-Class system for tkinter GUI
		-Interpreting server data 
		-MainMenu, JoinGame, HostGame classes
		-Syncing up clients on the server so everyone gets the same text and is in 1 'lobby' to determine winner
	Benjamin Rader:
		-design of tkinter gui and functionalites such as timer, main menu setup, help page,
		 results page, and the text box during the game.
		-GameScreen class and PostGame class
		-Score calculation
		-Prompt randomization