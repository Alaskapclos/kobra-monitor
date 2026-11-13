# SPDX-License-Identifier: GPL-3.0-only
"""The one external console command required by unmodified Spoolman startup."""
import io
import zipfile

MAC_ALEMBIC = '''#!/bin/sh
set -eu
native_bin=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec "$native_bin/python3.14" -I -B -m alembic "$@"
'''


def windows_alembic(launcher):
    # Distlib's documented <launcher_dir> marker keeps this executable portable
    # across extraction and user-install directories, including spaces.
    script=b'import sys\nfrom alembic.config import main\nif __name__ == "__main__":\n    sys.exit(main())\n'
    body=io.BytesIO()
    with zipfile.ZipFile(body,'w',zipfile.ZIP_STORED) as archive:
        info=zipfile.ZipInfo('__main__.py',(2026,1,1,0,0,0));archive.writestr(info,script)
    return launcher+b'#!"<launcher_dir>\\..\\python.exe" -B -X utf8\n'+body.getvalue()
