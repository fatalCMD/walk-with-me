# Victory reactions

On by default. Set `[PartyLife] bVictoryCelebrations=false` to disable.
After at least five distinct enemies die in one encounter, eligible companions
can briefly clap or cheer. Smaller separate fights do not add up.

The tracked party must leave combat/searching for 1.25 seconds. Only participating,
nearby humanoid followers with sheathed weapons can react. Starts are staggered;
accepted gestures last at most 2.6 seconds while safe to stop.

Waiting, dismissed, excluded or unsafe actors are skipped. Combat, dialogue,
scenes, a new order, moving away or loading cancels the reaction. It waits for
quest alias cleanup and restores normal travel afterward.

Uses Skyrim's IdleApplaud2, IdleApplaud5 and IdleCivilWarCheer. No new assets or
voices. Cleanup stops only the idle owned by this feature; another mod's replacement
is left alone. Replaying the same idle from another mod cannot always be distinguished.

Test four versus five enemies, fleeing/live enemies, interruptions and save/load.
Check transitions with your animation replacers. `[Victory]` log entries record
accepted playback, not visual quality.
