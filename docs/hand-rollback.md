# Hand rollback

In-game comparisons favored revision 11 over 11.1, 12 and 13. The later wrist,
attachment and heading experiments were rolled back. Passing pose tests had not
predicted those visual regressions.

Revision 11.2 then fixed velocity being cleared by scene updates, while keeping
revision 11's hand geometry. See hand-velocity.md. Wrist placement still needs work.
