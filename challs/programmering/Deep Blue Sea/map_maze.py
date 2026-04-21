#!/usr/bin/env python3
"""
Deep Blue Sea - Map the maze by probing walls.
Strategy: Try paths and see which ones hit walls vs don't.
Also collect shark positions to understand the grid and identify non-wall cells.
"""
from pwn import *
import json, time, re

context.log_level = 'error'

def try_path(path_str, wait_updates=1):
    """Send a path, return (result_type, shark_data)"""
    r = remote("undutmaning-deep.chals.io", 443, ssl=True, sni="undutmaning-deep.chals.io")

    # Read intro
    data = b""
    while b"informerar:" not in data:
        data += r.recv(4096, timeout=10)

    # Read first shark update
    shark_line = r.recvline(timeout=10).decode().strip()
    sharks = json.loads(shark_line)["sharks"]

    # Wait for more updates if needed
    all_sharks = [sharks]
    for _ in range(wait_updates - 1):
        try:
            r.recvuntil(b"informerar:\n", timeout=8)
            line = r.recvline(timeout=8).decode().strip()
            all_sharks.append(json.loads(line)["sharks"])
        except:
            break

    # Send path
    r.sendline(path_str.encode())

    # Get response
    time.sleep(2)
    try:
        response = r.recv(4096, timeout=5).decode('utf-8', errors='replace').strip()
    except:
        response = ""

    r.close()

    if "vägg" in response:
        return "WALL", all_sharks, response
    elif "haj" in response:
        return "SHARK", all_sharks, response
    elif "vilse" in response:
        return "LOST", all_sharks, response
    elif "undut{" in response:
        return "FLAG", all_sharks, response
    else:
        return "OTHER", all_sharks, response

# First, collect shark positions to understand the grid
print("=== COLLECTING SHARK DATA ===")
all_shark_positions = set()
for attempt in range(3):
    r = remote("undutmaning-deep.chals.io", 443, ssl=True, sni="undutmaning-deep.chals.io")
    data = b""
    start = time.time()
    while time.time() - start < 30:
        try:
            chunk = r.recv(4096, timeout=2)
            data += chunk
        except:
            pass
    r.close()

    # Parse all shark positions
    for match in re.finditer(r'"sharks": \[([^\]]+\])\]', data.decode('utf-8', errors='replace')):
        sharks = json.loads("[" + match.group(1) + "]")
        for pos in sharks:
            all_shark_positions.add(tuple(pos))

print(f"Collected {len(all_shark_positions)} unique shark positions")
rows = sorted(set(p[0] for p in all_shark_positions))
cols = sorted(set(p[1] for p in all_shark_positions))
print(f"Row range: {min(rows)}-{max(rows)}")
print(f"Col range: {min(cols)}-{max(cols)}")
print(f"All positions: {sorted(all_shark_positions)}")

# Now probe directions from start
# We don't know starting position yet
# Try: which single directions are walls?
print("\n=== PROBING SINGLE STEPS ===")
for d in ["N", "S", "Ö", "V"]:
    result, sharks, resp = try_path(d)
    print(f"  {d}: {result} — {resp[:60]}")

# Try longer paths in each direction
print("\n=== PROBING 2-STEP PATHS ===")
for d1 in ["N", "S", "Ö", "V"]:
    for d2 in ["N", "S", "Ö", "V"]:
        result, sharks, resp = try_path(d1+d2)
        if result != "WALL":
            print(f"  {d1}{d2}: {result} — {resp[:60]}")
        else:
            print(f"  {d1}{d2}: WALL")
