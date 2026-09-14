"""Read-only movement hook audit against a user's executable and Address Library.

Requires capstone for disassembly. Does not load or run the executable.
"""
import argparse
import hashlib
import struct
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('executable', type=Path)
parser.add_argument('database', type=Path)
parser.add_argument('--player-vtable-id', type=int, required=True)
args = parser.parse_args()
b = args.database.read_bytes()
cursor = 0

def read(fmt):
    global cursor
    value = struct.unpack_from('<' + fmt, b, cursor)
    cursor += struct.calcsize('<' + fmt)
    return value[0] if len(value) == 1 else value

fmt = read('I')
version = read('4I')
mapping = {}
if fmt in (1, 2):
    name_length = read('I')
    cursor += name_length
    pointer_size, count = read('2I')
    previous_id = previous_offset = 0

    def decode(kind, previous):
        if kind == 0: return read('Q')
        if kind == 1: return previous + 1
        if kind == 2: return previous + read('B')
        if kind == 3: return previous - read('B')
        if kind == 4: return previous + read('H')
        if kind == 5: return previous - read('H')
        if kind == 6: return read('H')
        if kind == 7: return read('I')
        raise ValueError('Invalid address encoding')

    for _ in range(count):
        kind = read('B')
        identifier = decode(kind & 15, previous_id)
        high = kind >> 4
        offset = decode(high & 7, previous_offset // pointer_size if high & 8 else previous_offset)
        if high & 8: offset *= pointer_size
        mapping[identifier] = offset
        previous_id, previous_offset = identifier, offset
elif fmt == 5:
    cursor += 64
    pointer_size, data_format, count = read('3I')
    assert pointer_size == 8 and data_format == 0
    mapping = {identifier: read('I') for identifier in range(count)}
else:
    raise ValueError('Unsupported Address Library format')

exe = args.executable.read_bytes()
pe = struct.unpack_from('<I', exe, 0x3c)[0]
assert exe[pe:pe + 4] == b'PE\0\0'
section_count = struct.unpack_from('<H', exe, pe + 6)[0]
optional_size = struct.unpack_from('<H', exe, pe + 20)[0]
base = struct.unpack_from('<Q', exe, pe + 24 + 24)[0]
sections = []
for i in range(section_count):
    pos = pe + 24 + optional_size + 40 * i
    if exe[pos:pos + 8].rstrip(b'\0') == b'.bind':
        parser.error('This Steam executable is packed; an unpacked image is required for an offline instruction audit.')
    virtual_size, rva, raw_size, raw = struct.unpack_from('<4I', exe, pos + 8)
    sections.append((rva, raw_size, raw, struct.unpack_from('<I', exe, pos + 36)[0]))

def raw_at(rva, length):
    for start, size, raw, flags in sections:
        if start <= rva and rva + length <= start + size:
            return exe[raw + rva - start:raw + rva - start + length], flags
    raise ValueError(f'RVA {rva:x} is not backed by executable file data')

ae = version[1] >= 6
function = mapping[37943 if ae else 37013]
site = function + (0x51 if ae else 0x1a)
instruction, flags = raw_at(site, 5)
print(f'Runtime {version}; function RVA {function:X}; candidate {site:X}: {instruction.hex()}; flags {flags:X}', flush=True)
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
disassembler = Cs(CS_ARCH_X86, CS_MODE_64)
code, _ = raw_at(function, 160)
for item in disassembler.disasm(code, base + function):
    print(f'  {item.address:X}: {item.mnemonic} {item.op_str}', flush=True)
    if item.mnemonic == 'ret': break
assert flags & 0x20000000 and instruction[0] == 0xe8, 'Expected a direct call in executable code'
target = site + 5 + struct.unpack_from('<i', instruction, 1)[0]
_, flags = raw_at(target, 32)
assert flags & 0x20000000, 'Call target is not executable'
vtable = mapping[args.player_vtable_id]
entry, _ = raw_at(vtable + 0xad * 8, 8)
update = struct.unpack('<Q', entry)[0] - base
_, flags = raw_at(update, 16)
assert flags & 0x20000000, 'Player update entry is not executable'
print(f'Runtime {version}; EXE SHA256 {hashlib.sha256(exe).hexdigest()}')
print(f'Speed function RVA {function:X}, call {site:X}, target {target:X}; Player update RVA {update:X}')

from capstone import Cs, CS_ARCH_X86, CS_MODE_64
disassembler = Cs(CS_ARCH_X86, CS_MODE_64)
for label, start, length in [('speed function', function, 128), ('speed factor', target, 128)]:
    print(label)
    code, _ = raw_at(start, length)
    for instruction in disassembler.disasm(code, base + start):
        print(f'  {instruction.address:X}: {instruction.mnemonic} {instruction.op_str}')
        if instruction.mnemonic == 'ret': break
