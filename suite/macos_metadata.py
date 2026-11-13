# SPDX-License-Identifier: GPL-3.0-only
"""Remove only Finder decoration from generated app copies; retain security metadata."""
import os
from pathlib import Path
import sys


def clean_packaging_metadata(app):
    # Only Finder decoration/resource forks on generated build copies prevent
    # codesign. Never clear quarantine, provenance or other security metadata.
    if sys.platform!='darwin':return
    import ctypes as c
    libc=c.CDLL('/usr/lib/libSystem.B.dylib',use_errno=True)
    libc.listxattr.argtypes=[c.c_char_p,c.c_void_p,c.c_size_t,c.c_int]
    libc.listxattr.restype=c.c_ssize_t
    libc.removexattr.argtypes=[c.c_char_p,c.c_char_p,c.c_int]
    libc.removexattr.restype=c.c_int
    for path in [Path(app),*Path(app).rglob('*')]:
        encoded=os.fsencode(path);size=libc.listxattr(encoded,None,0,1)
        if size<0 or size>65536:raise OSError(c.get_errno(),'Mac-Baumetadaten konnten nicht gelesen werden.')
        if not size:continue
        buffer=c.create_string_buffer(size)
        if libc.listxattr(encoded,buffer,size,1)<0:raise OSError(c.get_errno(),'Mac-Baumetadaten änderten sich.')
        names=buffer.raw.split(b'\0')
        for name in (b'com.apple.FinderInfo',b'com.apple.ResourceFork'):
            if name in names and libc.removexattr(encoded,name,1)<0:
                raise OSError(c.get_errno(),'Finder-Baumetadaten konnten nicht entfernt werden.')

