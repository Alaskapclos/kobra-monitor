# SPDX-License-Identifier: GPL-3.0-only
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from suite.macos_bundle import build

parser=argparse.ArgumentParser(description='Build the isolated native Mac test app from verified local inputs.')
parser.add_argument('--architecture',choices=['x86_64','arm64'],default='x86_64')
parser.add_argument('--inputs',required=True);parser.add_argument('--destination',required=True)
parser.add_argument('--camera-input', nargs=2, metavar=('ZIP', 'SHA256'),
                    help='Use a verified optional FFmpeg camera kit.')
args=parser.parse_args()
print(json.dumps(build(args.inputs,Path(__file__).resolve().parent.parent,args.destination,architecture=args.architecture,camera_input=args.camera_input),indent=2))
