from pathlib import Path
import struct
b=Path(r'..\MODS\mods\SKSE Menu Framework\SKSE\Plugins\fonts\fa-solid-900.ttf').read_bytes()
u16=lambda o:struct.unpack_from('>H',b,o)[0]
u32=lambda o:struct.unpack_from('>I',b,o)[0]
tables={b[12+i*16:16+i*16]:u32(20+i*16) for i in range(u16(4))}
o=tables[b'cmap'];offsets=[o+u32(o+8+i*8) for i in range(u16(o+2))];codes=[0xf14e,0xf024,0xf132,0xf06d,0xf554,0xf0c0,0xf084,0xf007]
def glyph(base,c):
 if u16(base)==4:
  n=u16(base+6)//2;end=base+14;start=end+2*n+2;delta=start+2*n;ran=delta+2*n
  for i in range(n):
   if u16(start+2*i)<=c<=u16(end+2*i):
    r=u16(ran+2*i);g=u16(ran+2*i+r+2*(c-u16(start+2*i))) if r else c
    return (g+u16(delta+2*i))&65535 if g else 0
 if u16(base)==12:
  for i in range(u32(base+12)):
   lo,hi,g=struct.unpack_from('>III',b,base+16+12*i)
   if lo<=c<=hi:return g+c-lo
 return 0
assert all(any(glyph(base,c) for base in offsets) for c in codes)
print('Verified eight solid icon glyphs in the installed font.')
