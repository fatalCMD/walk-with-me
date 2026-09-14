# Usage

## Requirements

Use the dependencies listed for your download. See release.md in the source,
or README.md in the mod archive. Command gestures have extra requirements below.

## Install or update

Close Skyrim. Replace the old mod in MO2 or Vortex and enable `Wayfarer.esp`.
Keep `SKSE/Plugins/Wayfarer.ini` to retain settings. Start the game through SKSE.
Do not rename the Wayfarer DLL, ESP, scripts or INI; saves and other mods use them.

## Party

Current and newly recruited followers join automatically as they load nearby, up
to the companion limit (10 maximum). No new game or manual Add is needed.

Open Walk With Me in Menu Framework to manage Party. **Remove** releases control
and prevents automatic re-addition without dismissing them. **Add** allows them
back. These choices are saved. Older INIs enable automatic enrollment once on
upgrade; turning it off afterward stays saved. Other preferences are retained.

Custom followers must expose their recruitment through teammate state. Followers
with private recruitment systems may need manual Add or an API integration.

**Enforce custom followers** is on by default. Disable it to let their own AI take
over, or exclude one follower. NFF enforcement has a separate setting. Wait orders,
dismissal, combat and scripted scenes still take priority.

## Orders

- Natural: followers choose their positions.
- Lead: walk ahead.
- Companion: walk beside you.
- Rear: follow behind.
- Relax: stay near the rest point until another order.
- Vanilla: return control to Skyrim or your follower framework.

Open the wheel with its assigned key. Use 1-6, arrows and Enter, or mouse clicks.
Escape closes it. On gamepad, hold LB and click the right stick; aim with the
right stick, confirm with A, cancel with B. Releasing the stick issues no order.

Change keys under Controls. Shift, Ctrl and Alt combinations work; matching is
exact. Escape cancels capture, Delete clears it. See hotkeys.md in the source.

## Travel and rest

Adjust spacing, catch-up speed and turn delay under Travel. The default turn
delay is 0.22 seconds. Companion individuality defaults to 1; use 0 for shared pace.

Temporary rest ends when you leave its range. Relax stays active until another
order. Activities need nearby furniture, idles and connected navigation.
Stairs and ramps work within the height limit; load doors are not crossed.

Walking banter is on by default. Eligible pairs can talk while moving, but scenes
with their own packages or other restrictions keep control. No voiced lines are added.
Victory reactions are on by default after a fight with at least five enemies.

## Gestures and hand holding

Command hand signals are optional. Third-person Lead, Companion and Rear clips
are included, with female variants. First-person clips come from First Person
Interactions. Install FPI, Open Animation Replacer and GP Offset Movement
Animation, then generate its behavior with Nemesis or a compatible Pandora setup.
Gestures skip busy states. Vanilla has no signal. Gesture Animation Remix is not needed.

Hand holding is experimental and off by default. Select one follower and use
Companion mode in third person. Walking and running work; sprinting releases it.
Wrist twisting and awkward turns remain. See hand-holding.md in the source or
HAND_HOLDING.md in the archive.

## Problems

Send your runtime version, follower mods, location and `Walk With Me.log`.
The log is in your game's SKSE log folder. Include video for animation problems.

Gesture setup: see docs/gestures.md in the source or GESTURES.md in the mod ZIP.
The GPMA patch is included. Let its files win over GPMA, then regenerate with your
existing Nemesis or Pandora setup. Do not replace another modlist's generated graph.
