"""Merge a user's INI into staged public defaults without changing the source INI."""
from pathlib import Path
import argparse
import configparser
import io
import re

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('settings', type=Path, help='INI whose preferences become release defaults')
args = parser.parse_args()
staged = root / 'package/SKSE/Plugins/Wayfarer.ini'
if args.settings.resolve() == staged.resolve():
    parser.error('Source settings must be separate from the staging INI.')
original = args.settings.read_bytes()

def read_config(text):
    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str
    config.read_string(text)
    return config

baseline = read_config(staged.read_text(encoding='utf-8-sig'))
installed = read_config(original.decode('utf-8-sig'))
for section in installed.sections():
    if not baseline.has_section(section):
        baseline.add_section(section)
    for key, value in installed.items(section):
        baseline[section][key] = value

version = re.search(r'project\(Wayfarer VERSION ([0-9.]+)',
                    (root / 'CMakeLists.txt').read_text()).group(1)
out = io.StringIO()
baseline.write(out)
staged.write_text(
    f'; Walk With Me {version}. Settings save immediately from the configuration menu.\n'
    '; Compatibility filenames and plugin identifiers retain Wayfarer.\n' + out.getvalue().rstrip() + '\n',
    encoding='utf-8')
result = read_config(staged.read_text(encoding='utf-8'))
for section in installed.sections():
    for key, value in installed.items(section):
        assert result[section][key] == value
assert args.settings.read_bytes() == original, 'Source settings changed during preparation'
print('Public defaults match supplied settings; newer staged defaults retained. Source INI unchanged.')
