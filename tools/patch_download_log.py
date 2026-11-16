#!/usr/bin/env python3
"""Keep diagnostic logs outside mounted game images."""
import argparse
from pathlib import Path
import re

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--check", action="store_true")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
source = root / "src/dlc_modules/dlc_config.h"
data = source.read_bytes()
pattern = rb'#define SCE_DLC_EMU_LOG_PATH "(/[^"\r\n]*/dlc_emu\.log)"'
matches = list(re.finditer(pattern, data))
if len(matches) != 1:
    raise SystemExit("DLC log implementation changed; review before building")
target = b"/download/dlc_emu.log"
path = matches[0].group(1)
if args.check:
    if path != target:
        raise SystemExit(f"Unexpected diagnostic log path: {path!r}")
else:
    source.write_bytes(data.replace(path, target))
    doc = root / "README.md"
    doc.write_bytes(doc.read_bytes().replace(path, target))
print("Diagnostic log: /download/dlc_emu.log")
