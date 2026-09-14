# Custom followers

Automatic enrollment and custom enforcement are on by default. The periodic scan
adds existing companions and later recruits when they load nearby, up to the party
limit. Wayfarer assigns its travel and rest packages at runtime; no follower patch
or behavior generation is needed for enrollment. Command gestures are separate.

Followers that never expose teammate status need manual Add or an API integration.
This does not recruit NPCs or replace a follower manager's quests and dialogue.

Custom enforcement is on by default. Recruited custom teammates can bypass
the vanilla follower faction and ordinary travel package requirements. Wait,
dismissal, combat and scene guards remain. Custom blocklists and exclusions stay;
the old default blocklist migrates away.

Serana's own recruitment path can set teammate status without CurrentFollowerFaction.
Inigo can use a negative WaitingForPlayer value for dismissal. Detection must respect
both cases. These were record/script findings, not proof that every follower works.
Test package ownership and handoff with each framework.
