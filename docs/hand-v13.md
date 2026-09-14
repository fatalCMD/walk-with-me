# Hand revision 13

Rejected experiment; rolled back after worse in-game results than revision 11.

XPMSSE inserts CME connectors between arm and finger bones. Revision 12's filter
stopped traversal at those connectors, leaving stale world transforms for IK.
Revision 13 addressed that traversal issue. Its tests did not establish an acceptable
in-game pose. See hand-rollback.md; current movement is documented in hand-holding.md.
