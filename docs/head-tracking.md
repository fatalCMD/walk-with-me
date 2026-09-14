# Head tracking

**Glance toward followers** is on by default for command gestures.
INI: `[Interface] bGestureAwareness`.

Loaded managed followers within 900 horizontal and 200 vertical units each get
one vote. A group behind requests up to 28 degrees; alongside, up to 8 degrees.
Balanced or front groups stay neutral. The target eases in over 0.3 seconds and
out over 0.4 seconds. It does not turn the body or camera.

Existing dialogue, combat, script and procedure head targets take priority.
TDM is optional; target lock or a refused API handoff skips the glance.
Borrowed flags and the TDM handoff are restored when the gesture ends.

First person, a camera near the head or a busy state cancels it. Loading restores
cleanup state without replaying the gesture. Test with your camera, skeleton and
headtracking mods; actual bone rotation depends on the behavior graph.
