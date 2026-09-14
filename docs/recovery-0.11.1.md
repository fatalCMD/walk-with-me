# Travel recovery 0.11.1

The log showed a stationary follower with an alias but no owned package.
The watchdog now checks displacement and goal distance even before package ownership
is accepted. Moving and arrived actors are left alone. On timeout, release the lease;
wait for Papyrus alias removal and cooldown before reacquiring. Unaccepted handoffs
get one second between evaluation retries. The old log did not identify the competing
package, and its saved-script warning alone did not prove the cause.
