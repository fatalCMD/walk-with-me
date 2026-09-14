# Stairs and floors 0.15.1

Activity searches retain target height and follow loaded navmesh connections.
Stacked coordinates do not connect floors. Door, drop and missing links are excluded.
The search settles at most 2048 nodes and uses a route budget of clamp(radius*4,
1200,5000). It checks up to eight candidates with three approach offsets each.
Default height is 768, configurable from 64 to 1600. Unvisited nodes remain unavailable
when the budget runs out. Arrival checks include height.
