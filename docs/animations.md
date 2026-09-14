# Command animations

The early Lead, Companion and Rear clips use selectors 911/912/913 and masks
2/0/1. Clips last 2.4 seconds; blend-out starts at 2.35. First person keeps its
FPI fallbacks. Later shared gestures are described in gesture-rest.md.

Lead points forward, Rear pulls an open hand back and Companion beckons with both
arms. The generator uses 73 samples at 30 fps. The lower body stays constant;
walking still needs the correct behavior mask.

## Generate

Needs Python, NumPy, SciPy, Pillow, a local vanilla 99-bone skeleton and the
anim_skyrim.py/anim_fo4.py modules from
[PyNifly](https://github.com/BadDogSkyrim/PyNifly/tree/1f73b83f9bafb4cb070190d1f3b8478198c337b3).
Use an output folder that does not exist:

```powershell
python tools/prototype-command-animations.py `
  --skeleton build/animation-preview/skeleton.hkx `
  --exporter build/original-gestures/pynifly `
  --python-deps build/animation-preview/deps `
  --output build/original-gestures/studies-v6
```

Use `--style female` for the variant from `tools/elegant_command_motion.py`.
Validate with `tools/validate-prototype-animations.py`; stage with
`tools/prepare-prototype-signals.py` and `--female` for that variant.
The staging helper can copy locally installed FPI fallbacks. The release packager
excludes those first-person clips.

## Timing fix

V5 used clip duration as block duration and swung incorrectly in game. V6 uses
`(256-1)/30 = 8.5` for block duration and updates its reciprocal. Poses were unchanged.
The user confirmed the timing fix worked. Keep the independent decoder/timing checks.

The 0.16.2 package includes original third-person clips and female variants.
No first-person FPI or Gesture Animation Remix clips are redistributed.
Check skinning, clothes, wrists and walking in game; valid HKX data alone is not enough.
