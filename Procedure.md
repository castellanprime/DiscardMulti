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
