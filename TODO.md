Date: July 23, 2018	Bug: 1
==============================

- Fixed JSON encoding of roomates by replacing roomate object with just the 
user id
- BUG: After users have joined, if one user elects to see the roomates, 
the other user can not see the roomates since the server becomes busy
serving the requests of the other that saw the roomates list. This is 
because the one that saw the roomates list is querying constantly for
feedback on whether all the members of the game room have joined
- TODO: To fix above bug.

Date: July 24, 2018	Bug: 2 
===============================

- Fixed the above bug. The problem was that subsequent connections from 
new clients were not being created and added to the list of game connections.
- BUG: After a new user joins, the server stops sending messages and hangs.
- TODO: To fix Bug 2

Date: July 25, 2018	Bug 3
===============================

- Fixed the above bug. The problem was that I was not checking for that
the room should not have started,
- BUG: Once a new user joins, the server pauses to wait for messages from the
person who created the room in the first place. The joining user(s) hang and 
cant send any new messages.
- TODO: To fix Bug 3

Date: July 27, 2018 	Redesign 1
==================================

- Implement a way to push notifications instead of polling
during initial connections
