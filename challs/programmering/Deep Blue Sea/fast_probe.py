#!/usr/bin/env python3
"""
Deep Blue Sea - Fast maze probing.
We know from initial probing:
- Start at (0,0), N=wall, V=wall, S=open, Ö=open
- S corridor: (1,0): only S works (Ö=wall, V=wall)
- Ö corridor: (0,1): only Ö works (N=wall, S=wall)
- Ö×7 = wall, so east corridor is 6 cells long (0,1)-(0,6)

Strategy: The maze is narrow corridors. Probe systematically by extending
known corridors and finding turns.
"""
from pwn import *
import time, sys

context.log_level = 'error'

def try_path(path_str):
    """Returns WALL, OPEN, or FLAG"""
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
        time.sleep(1.5)
        resp = b""
        try:
            resp = r.recv(4096, timeout=5)
        except:
            pass
        r.close()
        resp_str = resp.decode('utf-8', errors='replace')
        if "vägg" in resp_str:
            return "WALL"
        elif "undut{" in resp_str:
            return "FLAG: " + resp_str
        elif "batteri" in resp_str.lower() or "karta" in resp_str.lower() or "grattis" in resp_str.lower():
            return "SPECIAL: " + resp_str[:300]
        else:
            return "OPEN"
    except Exception as e:
        return f"ERROR: {e}"

# Known maze structure so far:
# (0,0) start -> S corridor goes south
# (0,0) start -> Ö corridor goes east to (0,6)
# From (1,0): SS works, SÖ=wall, SV=wall
# From (0,6): Ö=wall (7th east). Need to check N, S, V from here.

print("=== EXPLORING EAST CORRIDOR END (0,6) ===")
# At (0,6), Ö is wall. Check N and S.
for d in ['N', 'S']:
    path = 'ÖÖÖÖÖÖ' + d
    result = try_path(path)
    print(f"  ÖÖÖÖÖÖ{d}: {result}")

# Explore south from east corridor end
# Maybe there's a turn at (0,6) going south?
if True:  # Let's check deeper
    print("\n=== SOUTH CORRIDOR DEPTH ===")
    for depth in range(3, 30):
        path = 'S' * depth
        result = try_path(path)
        print(f"  S×{depth}: {result}")
        if result == "WALL":
            print(f"  South corridor ends at depth {depth}")
            south_depth = depth - 1
            break
    else:
        south_depth = 29

    # At the end of south corridor, check turns
    print(f"\n=== SOUTH CORRIDOR END (depth={south_depth}) ===")
    base = 'S' * south_depth
    for d in ['Ö', 'V', 'S']:
        result = try_path(base + d)
        print(f"  {base[:5]}...{d}: {result}")

    # If there's a turn, explore further
    # Let's also check for turns at each point in the south corridor
    print("\n=== CHECKING TURNS IN SOUTH CORRIDOR ===")
    for depth in range(2, south_depth + 1):
        base = 'S' * depth
        for d in ['Ö', 'V']:
            key = f"S×{depth}+{d}"
            result = try_path(base + d)
            if result != "WALL":
                print(f"  *** TURN FOUND: {key} -> {result}")
                # Explore this branch
                branch_base = base + d
                for d2 in ['N', 'S', 'Ö', 'V']:
                    result2 = try_path(branch_base + d2)
                    if result2 != "WALL":
                        print(f"      {key}+{d2}: {result2}")
            # Only print walls for turns we're interested in
