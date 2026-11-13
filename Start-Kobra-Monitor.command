#!/bin/zsh
set -eu
cd -- "$(dirname -- "$0")"
for candidate in python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys;sys.exit(sys.version_info<(3,11))' >/dev/null 2>&1; then
    exec "$candidate" bootstrap.py --open
  fi
done
print 'Bitte Python 3.11 oder neuer installieren und den Starter erneut öffnen.'
read -k 1 '?Taste drücken zum Schließen.'
