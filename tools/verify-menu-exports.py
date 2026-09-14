"""Check used dynamic GUI entry points against the installed framework PE exports."""
from pathlib import Path
import re
import struct

root = Path(__file__).resolve().parents[1]
dll = root.parent / 'MODS/mods/SKSE Menu Framework/SKSE/Plugins/SKSEMenuFramework.dll'
b = dll.read_bytes()
def u32(offset): return struct.unpack_from('<I', b, offset)[0]
pe = u32(0x3c)
count = struct.unpack_from('<H', b, pe + 6)[0]
optional = struct.unpack_from('<H', b, pe + 20)[0]
sections = [struct.unpack_from('<IIII', b, pe + 24 + optional + i * 40 + 8) for i in range(count)]
def offset(rva):
    for virtual_size, virtual_address, raw_size, raw_start in sections:
        if virtual_address <= rva < virtual_address + max(virtual_size, raw_size):
            return raw_start + rva - virtual_address
    raise ValueError(hex(rva))
exp = offset(u32(pe + 24 + 112))
names = offset(u32(exp + 32))
exports = set()
for i in range(u32(exp + 24)):
    pos = offset(u32(names + i * 4))
    exports.add(b[pos:b.index(b'\0', pos)].decode())
header = (root / 'include/SKSEMenuFramework.h').read_text()
source = (root / 'src/menu_ui.cpp').read_text()+(root/'src/order_visuals.cpp').read_text()
used = set(re.findall(r'(?:Im|Draw|D)::(\w+)\(', source))
required = {'AddSectionItem', 'AddWindow', 'RegisterInpoutEvent', 'UnregisterInputEvent', 'RegisterHudElement', 'UnregisterHudElement', 'RegisterEventPriority', 'UnregisterEvent', 'GetMenuFrameworkVersion', 'IsAnyBlockingWindowOpened', 'SetHotkeyEnabled', 'IsHotkeyEnabled'}
for name in used:
    matches = re.findall(r'inline [^\n]*\b' + name + r'\([^{}]*?\)[^{]*\{(.*?)\n\s*\}', header, re.S)
    symbols = set()
    for body in matches:
        symbols.update(re.findall(r'GetMenuFrameworkFunction<[^>]+>\("([^"]+)"\)', body))
    assert symbols, f'No wrapper export found for {name}'
    required.update(symbols)
required.update({'PushSolid', 'Pop', 'LoadTexture', 'PushFont', 'ImFont_GetDebugName'})
missing = required - exports
assert not missing, f'Missing framework exports: {sorted(missing)}'
print(f'Menu verified: {len(required)} used GUI exports present in installed SKSE Menu Framework.')
