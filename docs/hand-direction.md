# Hand direction: revision 11

The early animation hook could write Speed/Direction before Skyrim refreshed those
channels. Logs sampled immediately after our write did not prove what the graph used.
Revision 11 applies gait after channel refresh and aligns the native walking target
with the pair's heading. It keeps revision 10's idle activation fix.
The Remiel video showed a facing mismatch; animation appearance still needed retesting.
