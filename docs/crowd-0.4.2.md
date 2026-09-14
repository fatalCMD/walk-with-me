# Crowds 0.4.2

Added deterministic destination reservations with 150-unit separation after grounding.
Nearby actors and floor height affected occupancy checks. The old 70-unit spacing
was smaller than two 65-unit arrival radii. The logs showed route handoffs, not direct
proof of actor collisions. This allocator was later removed in 0.5.
