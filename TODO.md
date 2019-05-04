Date: July 23, 2018	Bug: 1
--------------------------------

- Fixed JSON encoding of roomates by replacing roomate object with just the 
user id
- BUG: After users have joined, if one user elects to see the roomates, 
the other user can not see the roomates since the server becomes busy
serving the requests of the other that saw the roomates list. This is 
because the one that saw the roomates list is querying constantly for
feedback on whether all the members of the game room have joined
- TODO: To fix above bug.

Date: July 24, 2018	Bug: 2 
---------------------------------

- Fixed the above bug. The problem was that subsequent connections from 
new clients were not being created and added to the list of game connections.
- BUG: After a new user joins, the server stops sending messages and hangs.
- TODO: To fix Bug 2

Date: July 25, 2018	Bug 3
----------------------------------

- Fixed the above bug. The problem was that I was not checking for that
the room should not have started,
- BUG: Once a new user joins, the server pauses to wait for messages from the
person who created the room in the first place. The joining user(s) hang and 
cant send any new messages.
- TODO: To fix Bug 3

Date: July 27, 2018 	Redesign 1
----------------------------------

- Implement a way to push notifications instead of polling
during initial connections

Date: July 28, 2018	Redesign 2
----------------------------------

- Refactored code
- Think of different message formats for communication
(need a data type for incoming game messages)


Date: July 30, 2018	Redesign 3
----------------------------------

- Think of a way to yield from the game loop without breaking 
the loop( that is every where you have an input, replace that 
with a sort of "yield")

Date: August 1, 2018	Redesign 4
-----------------------------------

- Add a server for authorization and authentication and 
remove any authorization and authentication from the game 
server
- Figure how to connect pyzmq/tornado in the client, 
and websockets in the server(research)
- A possible architecture: 

> kivy/pyzmq(UI) - this should represented by the Player class
> netclient - this should be represented by the PlayerController class
> auth_server - this should be a Flask Server. Connected to the 
game_server with websockets. 
> game_server - this should be represented by the ServerController.
It also houses the chat server.

- Extract method for choosing options from a defined list of options

Date: August 2, 2018 	Redesign 5
-----------------------------------

- Use a decorator to log entry into a method and exit from a method
and turn it on only when versbose logging is requested by the user
- Investigate how to build a ncurses app(pyzmq) to communicate with the
tornado loop(net client) https://github.com/jnthnwn/zmq-chat

Date: August 7, 2018	Fixes
-----------------------------------

- Figured out a way to using pyzmq and tornado together and 
divided the user client from the networking part.

Date: Sept 4, 2018	Fixes
-----------------------------------

- Tested 90% of a way to using pyzmq and tornado together. So far
I have divided the client into the two parts: netclient(connecting to
game server), cmdui(for user input)
- TODO: Remove print methods. Add the game methods.


