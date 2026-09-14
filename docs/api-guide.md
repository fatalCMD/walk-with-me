# API

Public Wayfarer names are unchanged. Use actor reference FormIDs, not base NPC IDs.

## Papyrus

Add `package/Scripts/Source` to the compiler imports.

```papyrus
Wayfarer.RegisterFollower(MyFollower, 0)
Wayfarer.UnregisterFollower(MyFollower)
Wayfarer.ExcludeFollower(MyFollower)
Wayfarer.SetFormationMode(2)
```

Modes: 0 Natural, 1 Lead, 2 Companion, 3 Rear, 4 Relax, 5 Vanilla.
Slots 0-9 remain for compatibility; users cannot place them manually.

External registrations must be repeated after loading. Exclusions persist per save.
`SetDialogueManagement(actor, true/false)` is the saved Add/Remove path used by
Party and follower dialogue. It is separate from external registration.

Automatic enrollment defaults off. Explicit registration still works. Custom
integrations should register only while following and unregister before scripted behavior.

## C++

Include `WayfarerAPI.h`. Find `Wayfarer.dll`, resolve `Wayfarer_GetInterface` with
`GetProcAddress` and request version 1. Call mutating methods on the game thread.

`IsManaged` reports roster membership, including temporary AI release. It does
not prove that Wayfarer owns the active package.

`GetSlotFollower`, `GetSlotMarker` and `ReportAliasSync` are internal quest-bridge
calls. Other mods must not move the markers, fill aliases or report sync state.
Install matching DLL and Papyrus files.
