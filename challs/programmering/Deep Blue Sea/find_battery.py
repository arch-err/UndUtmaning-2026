#!/usr/bin/env python3
"""
Deep Blue Sea - Find the battery by exploring frontier cells
and trying round-trip paths.
"""
from pwn import *
import json, time, sys

context.log_level = 'error'

DIRS = {'N': (-1,0), 'S': (1,0), 'Ö': (0,1), 'V': (0,-1)}
REVERSE_DIR = {'N': 'S', 'S': 'N', 'Ö': 'V', 'V': 'Ö'}

def try_path(path_str):
    try:
        r = remote("undutmaning-deep.chals.io", 443, ssl=True, sni="undutmaning-deep.chals.io")
        data = b""
        for _ in range(20):
            try:
                chunk = r.recv(4096, timeout=2)
                data += chunk
                if b'"sharks"' in chunk:
                    break
            except:
                pass
        time.sleep(0.3)
        r.sendline(path_str.encode('utf-8'))
        time.sleep(2)
        resp = b""
        try:
            resp = r.recv(8192, timeout=8)
        except:
            pass
        r.close()
        resp_str = resp.decode('utf-8', errors='replace')
        if "vägg" in resp_str:
            return "WALL", resp_str
        elif "undut{" in resp_str:
            return "FLAG", resp_str
        elif "haj" in resp_str:
            return "SHARK", resp_str
        elif "vilse" in resp_str:
            return "LOST", resp_str
        elif "batteri" in resp_str.lower() or "grattis" in resp_str.lower():
            return "SPECIAL", resp_str
        else:
            return "OTHER", resp_str[:200]
    except Exception as e:
        return "ERROR", str(e)

def reverse_path(path_str):
    """Reverse a path to go back to start"""
    return ''.join(REVERSE_DIR[c] for c in reversed(path_str))

# Load maze data
with open('maze_full.json') as f:
    mdata = json.load(f)

paths = {tuple(int(x) for x in k.split(',')): v for k, v in mdata['paths'].items()}

# Frontier cells sorted by distance from start (try farthest first)
frontier_info = [
    ((11, 0), "SSSSÖSSSSVSSS"),
    ((10, -1), "SSSSVSVSSSÖSS"),
    ((10, 1), "SSSSÖSSSSVSSÖ"),
    ((9, -2), "SSSSVSVSSSÖSV"),
    ((8, -5), "SSSSVSVSVSVVS"),
    ((7, -6), "SSSSVSVSVSVVV"),
    ((7, 6), "SSSSÖÖÖSÖSSÖÖ"),
    ((6, 7), "SSSSÖÖÖSÖÖÖÖS"),
    ((6, 5), "SSSSÖÖÖSÖSSÖN"),
    ((4, 8), "SSSÖÖÖÖÖÖÖSÖ"),
    ((-2, 8), "ÖÖÖÖNVNÖÖÖÖÖ"),
    ((-3, -2), "SSSVNNVNNNN"),  # wait, this goes N a lot
    ((-1, -4), "SSSVNNVNVVN"),
    ((1, -4), "SSSVNNVNVVS"),
    ((2, -5), "SSSVNVSVNVV"),
]

# Strategy 1: Try round-trip paths to frontier cells
# The battery might be AT a frontier cell or ONE STEP BEYOND
print("=== STRATEGY 1: Round trips to frontier cells ===")
sys.stdout.flush()

for pos, path in frontier_info:
    # Try round trip directly to this cell
    round_trip = path + reverse_path(path)
    result, resp = try_path(round_trip)
    print(f"  Round trip to {pos} ({len(round_trip)} steps): {result}")
    if result == "FLAG":
        print(f"\n🚩🚩🚩 FLAG FOUND!")
        print(resp)
        sys.exit(0)
    elif result not in ("LOST", "SHARK"):
        print(f"    Interesting: {resp[:200]}")
    sys.stdout.flush()

# Strategy 2: Try going ONE step further from frontier cells in each direction
print("\n=== STRATEGY 2: One step beyond frontier ===")
sys.stdout.flush()

for pos, path in frontier_info:
    for d in DIRS:
        extended = path + d
        round_trip = extended + reverse_path(extended)
        result, resp = try_path(round_trip)
        if result == "FLAG":
            print(f"\n🚩🚩🚩 FLAG! Path to {pos}+{d}")
            print(resp)
            sys.exit(0)
        elif result == "WALL":
            pass  # wall in that direction
        elif result == "LOST":
            pass  # didn't find battery
        elif result == "SHARK":
            print(f"  {pos}+{d}: SHARK (path valid, try again!)")
        else:
            print(f"  {pos}+{d}: {result} — {resp[:200]}")
        sys.stdout.flush()

print("\nBattery not found at frontier +1. Need deeper exploration.")
