General approach
----------------

So when the client connects:

- The client requests for a list of rooms.
 
> - If there are rooms that are not full, the server responds with a list.
> > - The client then prompts the user to choose from the set.
> > - The client then prompts the user to input their name.
> > - The client requests a 'join room' from the server.
> > - The server responds with a success prompt.  
> - Else it tells the user that there are none. 
> > - The client then prompts the user to create a room.
> > - The user inputs a room name and a number of players to be housed in that room.
> > - The client then requests a 'room creation' from the server. 
> > - The server responds with a room id

- The client then connects to the game handler. 

> - The server check to see for the (userid, roomid) if a PeriodicCallback has
been initialized for it. If it has not, it initializes for it for every 
four seconds. This PeriodicCallback sends the list of roomates.  
> - The server then sends a success prompt indicating that the client has 
successfully connected.
> - Once the required number of clients are connected, the server stops the 
PeriodicCallback for every clients in the room and sends all of them a
'game begin' message.

Instructions for Periodic Callback: 
https://stackoverflow.com/questions/19542333/websocket-server-sending-messages-periodically-in-python/19571205#19571205 


- General format for messages should be

> - cmd: ServerEnum or ClientEnum
> - payload: Payload associated with a cmd
> > - prompt: For display on client
> > - data: For any integers, lists, etc
> > - nextCmd: For any other cmd that might be triggered on receiving the message

- Scenario A:

> -  If a user A starts creating a room on the server and other users connect to 
the server while user A is still creating it,
 
> > - this server should indicate to the other users that a room is being created,
> > - this server should make the users wait for the server to get the room id before they can join, but also should give them to continue waiting or create their own room

- Scenario B:

> If a user A leaves a game, do some procedures:

> > 1.  the user sends a game message to the server 
> > 2.  the server then pauses the game, saves the game state and discards any pending messages.
> > 3.  the server then sends back the players' state to the respective player.
> > 4.  the user then saves the game, and sends a leave command to the server.
> > 5.  the server then sends a broadcast message to all the players still in th game ,a create_a_computer message message, The server also sends back a leave_rep message to the player that sent the leave cmd.
> > 6.  the player which have received a leave_rep message closes websocket connection.
> > 7.  The players that have not been sent the leave cmd are given the option to add a Computer to replace the user that left. If one wants to leave, steps 1 - 7 is followed. If the players choose the Computer, the game is resumed. 