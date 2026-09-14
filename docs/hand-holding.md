# Hand holding

Experimental. Off by default. Wrist twisting, approach and turning can still look wrong.

## Setup

In Travel, choose one follower and enable **Hand holding**. Use Companion mode,
third person and sheathed weapons. The default lead-in is two seconds.
The selected follower approaches your hand; other party members are not substituted.

Walking, jogging and running are supported. Sprinting, combat, weapons, jumping,
swimming, mounting, dialogue, scenes, rest, first person, blocked movement or too
much separation release the grip. A new attempt starts with the lead-in again.

Collision between the selected follower and nearby characters is temporarily
changed during close approach and holding. Wall and terrain checks remain.
Borrowed collision and animation settings are restored on release.

## Current version

Uses hand-holding revision 11.2. It keeps revision 11's pose and fixes a scene
refresh that was clearing follower velocity. Later pose experiments were rolled
back after worse in-game results. See hand-velocity.md and hand-rollback.md in the source.

Custom skeletons, body proportions and animation replacers affect the result.
Tests cannot confirm how a grip looks in game.

For reports, include a video, which actor is on the left, movement state,
skeleton/animation mods and `Walk With Me.log`.
