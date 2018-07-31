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
> - messageid: track messages in the case of resumption
> - payload: Payload associated with a cmd
> > - `prompt`: For display on client
> > - `data`: For any integers, lists, etc
> > > For every communication with the client, the server has send the top
> > > card. This is where it would reside.
> > > For every communication with the server, the client has to send its
> > > response here.
> > - `return_type`: Used at the client for determing what to send back to
> > the server
> > - `flag`: Purpose is described in yielding from game loop
> > - `next_cmd`: Enums
> > > For communication to with the client, the server can do these options
> > > > - If the server is asking for an int, or str answer denoted by the
> > > > return_type argument, a PICK_OPTION would normally accompany the
> > > > originating message.
> > > > - If the server is asking for a list, a PICK_CARDS would normally
> > > > accompany the originating message and the player would be asked to
> > > > pick his/her card to play. 
> > > > - If there is no PICK_CARDS and the server is not asking for a list,
> > > >  then it means that the player has either made an error
> > > > ( played the wrong card) or there is a PICK_ONE, PICK_TWO 
> > > > associated with it, the player would have to pick cards from 
> > > > the general pile.  
> > - _extra_data: For cards for PICK_TWO, PICK_ONE, options

- Yielding from the game loop

> There is going to be two flags, a USER_INPUT_CONTINUE for 
continues that require some option to be chosen for user to then send
over cards he/she wants to use, a GAME_CONTINUE flag which denotes
where the game_loop was paused to go back to after the USER_CONTINUE flag
has been dropped.


> Operation

Server sends a message with GAME_MESSAGE_REP header, PICK_OPTION sub_header.
If the return type is INT or STR, the server saves the message, user_id, and
a flag USER_CONTINUE. 

Client receives said message and responds with GAME_MESSAGE header, data as
its choice, and the  

PICK_OPTION + return_type(INT or STR) -> server accepts and move

PICK_CARDS + no return_type = punishment/error
PICK_CARDS + return_type(LIST) = pick your own cards

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


- If 
