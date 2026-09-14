# Catch-up 0.2.1

Run starts at 350 units and stays active to 210. Jog starts at 220 and stays to 150.
Speed uses player pace plus a bounded closing correction. The forward route buffer
is excluded so followers do not brake on every marker refresh. Defaults: correction
cap 150 units/s, engine factor cap 1.5. Speed ramps; actual motion still depends on
turns, navigation and collisions. The old log did not record player speed.
