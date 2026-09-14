"""Read-only transparency checks for the generated HUD textures; requires Pillow."""
from pathlib import Path
from PIL import Image

root=Path(__file__).resolve().parents[1]/'package/Interface/Wayfarer'
for name in ('natural','lead','companion','rear','relax'):
    im=Image.open(root/f'hud-{name}.png')
    assert im.mode=='RGBA'
    alpha=im.getchannel('A')
    assert alpha.getextrema()==(0,255), f'{name}: requires opaque symbol and actual transparent background'
    width,height=im.size
    assert all(alpha.getpixel(p)==0 for p in ((0,0),(width-1,0),(0,height-1),(width-1,height-1))), f'{name}: opaque corner'
    histogram=alpha.histogram()
    clear=histogram[0]/(width*height)
    solid=sum(histogram[200:])/(width*height)
    assert clear>.15 and solid>.10, f'{name}: missing cutout or missing visible symbol'
    print(f'{name}: {width}x{height}, transparent={clear:.0%}, solid={solid:.0%}')
