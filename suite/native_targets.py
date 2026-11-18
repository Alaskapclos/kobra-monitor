# SPDX-License-Identifier: GPL-3.0-only
"""Explicit native targets; package identity never implies physical acceptance."""
from dataclasses import dataclass
import re
import platform as host_platform
import sys
import sysconfig


@dataclass(frozen=True)
class NativeTarget:
    family: str
    architecture: str
    platform: str
    wheel_platform: str
    cpu: int


TARGETS = {
    ('windows', 'x86_64'): NativeTarget('windows', 'x86_64', 'windows-x86_64', 'win_amd64', 0x8664),
    ('windows', 'arm64'): NativeTarget('windows', 'arm64', 'windows-arm64', 'win_arm64', 0xaa64),
    ('macos', 'x86_64'): NativeTarget('macos', 'x86_64', 'macos-x86_64', 'x86_64', 0x1000007),
    ('macos', 'arm64'): NativeTarget('macos', 'arm64', 'macos-arm64', 'arm64', 0x100000c),
}


def native_target(family, architecture):
    try:
        return TARGETS[(family, architecture)]
    except (KeyError, TypeError):
        raise ValueError('Unbekanntes natives Zielsystem oder unbekannte Architektur.') from None


def wheel_matches(tag, target):
    """The pinned CPython 3.14 ABI and exact CPU are required for native wheels."""
    parts = tag.split('-')
    if len(parts) != 3:
        return False
    python, abi, platform = parts
    if python in ('py3', 'py2.py3') and abi == 'none' and platform == 'any':
        return True
    if not ((python == 'cp314' and abi == 'cp314') or
            (re.fullmatch(r'cp3[0-9]+', python) and int(python[2:]) <= 314 and abi == 'abi3')):
        return False
    if target.family == 'windows':
        return platform == target.wheel_platform
    mac = re.fullmatch(r'macosx_(\d+)_(\d+)_(x86_64|arm64|universal2)', platform)
    return bool(mac and (int(mac[1]), int(mac[2])) <= (15, 0) and
                mac[3] in (target.architecture, 'universal2'))


def runtime_architecture():
    """Architecture of the running interpreter, including an Intel translated process."""
    if sys.platform == 'win32':
        # Windows may report the ARM64 host even for an emulated x64 process.
        # CPython's Windows build platform identifies the interpreter itself.
        architecture = {'win-amd64': 'x86_64', 'win-arm64': 'arm64'}.get(sysconfig.get_platform())
        if architecture is None:
            raise ValueError('Die laufende Windows-Python-Architektur wird nicht unterstützt.')
        return architecture
    machine = host_platform.machine().lower()
    aliases = {'x86_64': 'x86_64', 'amd64': 'x86_64', 'arm64': 'arm64', 'aarch64': 'arm64'}
    if machine not in aliases:
        raise ValueError('Die laufende Prozessorarchitektur wird nicht unterstützt.')
    return aliases[machine]
