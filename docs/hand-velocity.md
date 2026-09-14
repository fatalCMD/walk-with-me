# Hand velocity: revision 11.2

The Aela log showed 55 moving samples with zero physics velocity despite nonzero
requested speed. The wrist gap stayed at four units, pointing to movement state.

On Skyrim 1.5.97, Actor::Update3DPosition calls the controller position setter even
with warp=false. That setter clears velocity. Revision 11.2 uses the base
TESObjectREFR scene update and restores velocity after position writes.
Revision 11's pose remains. This fixes an engine-call error; live flicker and
animation appearance still need testing.
