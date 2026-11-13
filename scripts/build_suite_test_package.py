# SPDX-License-Identifier: GPL-3.0-only
"""Assemble an internal test installer, never deploy it."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from suite.bundle import assemble

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--image', required=True)
parser.add_argument('--source', required=True)
parser.add_argument('--destination', required=True)
args = parser.parse_args()
print(json.dumps(assemble(args.image, args.source, args.destination), indent=2))
