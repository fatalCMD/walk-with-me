# Hand-holding prototypes

Revision 8 required Character callbacks that were absent in local playtests.
Followers kept circling because startup could never finish. Revision 9 uses the
player-frame path to observe native movement or fresh graph activity instead.
Our own position correction cannot count as movement, and unchanged self-written
Speed cannot unlock readiness. Held gait speed no longer depends on NPC callbacks.

Later fixes cover idle startup, walking direction and velocity. See hand-startup.md,
hand-direction.md and hand-velocity.md. Current setup is in hand-holding.md.
