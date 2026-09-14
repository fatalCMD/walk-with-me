"""Package the default SE/AE release with the modern runtime reader and source."""
from pathlib import Path
import subprocess
import sys


def main():
    packager = Path(__file__).with_name('package-compatibility.py')
    subprocess.run(
        [sys.executable, '-X', 'utf8', str(packager), '--release', *sys.argv[1:]],
        check=True,
    )


if __name__ == '__main__':
    main()
