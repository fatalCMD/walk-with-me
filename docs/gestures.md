# Gesture setup

Use your existing Nemesis or Pandora setup. Installing a behavior engine alone
is not enough: regenerate after installing Walk With Me and its requirements.

## Install

1. Install [Open Animation Replacer](https://www.nexusmods.com/skyrimspecialedition/mods/92109),
   [First Person Interactions](https://www.nexusmods.com/skyrimspecialedition/mods/123129)
   and [Offset Movement Animation](https://www.nexusmods.com/skyrimspecialedition/mods/110408).
   Enable `FirstPersonInteractions.esp` and their required dependencies.
2. Install Walk With Me. Let it win file conflicts against Offset Movement Animation
   under `Nemesis_Engine/mod/gpma/0_master`. In MO2, put Walk With Me below GPMA
   in the left pane. In Vortex, set the matching file conflict rule and deploy.
3. Run your generator with the active mod list visible. For MO2, launch it through MO2.
   Keep your other required behavior patches enabled.

## Nemesis

Tick **GP Offset Movement Animation**, update the engine, then launch generation.
Enable the new output in your mod manager. See the
[GPMA author's steps](https://www.nexusmods.com/skyrimspecialedition/mods/110408).

## Pandora

Enable **GP Offset Movement Animation** and generate. Pandora reads Nemesis-format
patches, including this one. Direct output to a separate folder with `-o "path"`.
In MO2, enable that output mod. In Vortex, install the output as a mod and deploy.
See [Pandora setup](https://github.com/Monitor221hz/Pandora-Behaviour-Engine-Plus#quickstart).

There is no extra Walk With Me checkbox. The included files extend the GPMA patch.
Use the generator your list already supports; do not layer old Nemesis output over
new Pandora output, or the reverse. If your modlist has its own generation procedure,
follow it while keeping this patch visible.

## In game

Restart Skyrim. Enable **Command hand signal** in Walk With Me settings.
Enable Point for Lead and Invitation for Companion if you want those signals.
Try an order in third person with weapons sheathed, then while walking.
The legs should keep moving and the arms should return to rest.
First-person signals use the separately installed FPI clips.

## Patch and conflicts

The mod includes seven GPMA source files, built against GPMA 1.2. They add state 3
for Walk With Me's upper-body gestures. Full generated behavior HKXs are not shipped;
generate them for your own mod list. No separate patch download is needed.

The included patch was structurally checked against local Pandora output, including
the leg/root-motion layers. That does not confirm every animation or mod combination
in game. A fresh Nemesis generation has not been tested here. GPMA's author also
lists Nemesis and Pandora, with a note about testing Pandora 4.1.2.

If another mod edits the same GPMA files or claims state 3, those edits need a merge.
Do not assume choosing a file winner preserves both patches. FNIS alone does not
apply this Nemesis-format patch.

For missing gestures, check FPI/OAR requirements and that GPMA was enabled during
generation. For frozen legs or looping arms, check file conflicts and old output,
then regenerate. Send `Walk With Me.log`, the generator log and your behavior mods
if it still fails. Turn command signals off to keep using the follower features.
