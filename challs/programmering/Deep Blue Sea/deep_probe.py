#!/usr/bin/env python3
"""
Deep Blue Sea - Deep recursive maze probing.
Build full maze map using DFS, tracking all cells and their connections.
"""
from pwn import *
import time, json, sys

context.log_level = 'error'

DIRS = {'N': (-1, 0), 'S': (1, 0), 'Ö': (0, 1), 'V': (0, -1)}
REVERSE = {'N': 'S', 'S': 'N', 'Ö': 'V', 'V': 'Ö'}

def try_path(path_str):
    """Returns WALL, OPEN, or FLAG/SPECIAL"""
    for attempt in range(3):
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
            elif "karta" in resp_str.lower() or "batteri" in resp_str.lower() or "grattis" in resp_str.lower():
                return "SPECIAL: " + resp_str[:500]
            else:
                return "OPEN"
        except:
            time.sleep(0.5)
    return "ERROR"

def pos_from_path(path_str):
    r, c = 0, 0
    for ch in path_str:
        dr, dc = DIRS[ch]
        r += dr
        c += dc
    return (r, c)

# Build maze using BFS
open_cells = set()
open_cells.add((0, 0))
walls = set()
edges = {}  # (pos, dir) -> True/False
path_to = {(0, 0): ""}  # pos -> shortest path string from start

# Pre-load known data
known = {
    ((0,0), 'N'): False, ((0,0), 'V'): False,
    ((0,0), 'S'): True, ((0,0), 'Ö'): True,
    ((1,0), 'Ö'): False, ((1,0), 'V'): False, ((1,0), 'S'): True,
    ((2,0), 'Ö'): False, ((2,0), 'V'): False, ((2,0), 'S'): True,
    ((0,1), 'N'): False, ((0,1), 'S'): False, ((0,1), 'Ö'): True,
    ((0,6), 'Ö'): False, ((0,6), 'N'): True, ((0,6), 'S'): True,
    ((3,0), 'Ö'): True, ((3,0), 'S'): True,
    ((4,0), 'S'): False,  # S×5 = wall -> (5,0) is wall
    ((4,0), 'Ö'): True, ((4,0), 'V'): True,
}

# Populate edges and cells from known data
for (pos, d), is_open in known.items():
    edges[(pos, d)] = is_open
    if is_open:
        dr, dc = DIRS[d]
        new_pos = (pos[0]+dr, pos[1]+dc)
        open_cells.add(new_pos)
        open_cells.add(pos)
    elif not is_open:
        dr, dc = DIRS[d]
        wall_pos = (pos[0]+dr, pos[1]+dc)
        walls.add(wall_pos)

# Build initial path_to for known cells
# East corridor
for i in range(7):
    open_cells.add((0, i))
    path_to[(0, i)] = 'Ö' * i
# South corridor
for i in range(5):
    open_cells.add((i, 0))
    path_to[(i, 0)] = 'S' * i
# Turns
path_to[(3, 1)] = 'SSS' + 'Ö'
path_to[(4, 1)] = 'SSSS' + 'Ö'
path_to[(4, -1)] = 'SSSS' + 'V'
open_cells.add((3, 1))
open_cells.add((4, 1))
open_cells.add((4, -1))

# BFS frontier
from collections import deque
frontier = deque()

# Add unexplored edges from all known open cells
for pos in sorted(open_cells):
    for d in DIRS:
        if (pos, d) not in edges and pos in path_to:
            frontier.append(pos)
            break  # Only add each cell once

probe_count = 0
max_probes = 300

print(f"Starting with {len(open_cells)} known cells, {len(frontier)} frontier cells")
sys.stdout.flush()

while frontier and probe_count < max_probes:
    pos = frontier.popleft()

    if pos not in path_to:
        continue

    base_path = path_to[pos]

    for d in DIRS:
        if (pos, d) in edges:
            continue

        test_path = base_path + d
        result = try_path(test_path)
        probe_count += 1

        dr, dc = DIRS[d]
        new_pos = (pos[0]+dr, pos[1]+dc)

        if result == "WALL":
            edges[(pos, d)] = False
            walls.add(new_pos)
        elif result.startswith("FLAG") or result.startswith("SPECIAL"):
            print(f"\n!!! {result}")
            edges[(pos, d)] = True
            open_cells.add(new_pos)
            path_to[new_pos] = test_path
            sys.stdout.flush()
        else:  # OPEN (or SHARK - means path is valid)
            edges[(pos, d)] = True
            open_cells.add(new_pos)
            edges[(new_pos, REVERSE[d])] = True  # reverse is also open
            if new_pos not in path_to or len(test_path) < len(path_to[new_pos]):
                path_to[new_pos] = test_path
                frontier.append(new_pos)

        if probe_count % 10 == 0:
            print(f"  [{probe_count}] {len(open_cells)} cells, {len(walls)} walls, exploring {pos} dir {d} -> {result}")
            sys.stdout.flush()

# Print the final map
print(f"\n=== FINAL MAZE MAP ({probe_count} probes) ===")
print(f"Open cells: {len(open_cells)}")
sys.stdout.flush()

if open_cells:
    all_pos = open_cells | walls
    min_r = min(p[0] for p in all_pos)
    max_r = max(p[0] for p in all_pos)
    min_c = min(p[1] for p in all_pos)
    max_c = max(p[1] for p in all_pos)

    print(f"Grid: rows {min_r}-{max_r}, cols {min_c}-{max_c}\n")

    # Header with column numbers
    header = "     "
    for c in range(min_c, max_c + 1):
        header += str(abs(c) % 10)
    print(header)

    for r in range(min_r, max_r + 1):
        row_str = f"  {r:3d} |"
        for c in range(min_c, max_c + 1):
            if (r, c) == (0, 0):
                row_str += "S"
            elif (r, c) in open_cells and (r, c) in path_to:
                row_str += "."
            elif (r, c) in open_cells:
                row_str += "o"
            elif (r, c) in walls:
                row_str += "#"
            else:
                row_str += " "
        row_str += "|"
        print(row_str)

    # Print paths to farthest cells
    print("\n=== FARTHEST CELLS ===")
    for pos in sorted(path_to.keys(), key=lambda p: len(path_to[p]), reverse=True)[:10]:
        print(f"  {pos}: path length {len(path_to[pos])}, path: {path_to[pos]}")

    # Save maze data
    with open("maze_full.json", "w") as f:
        json.dump({
            "open_cells": sorted([list(p) for p in open_cells]),
            "walls": sorted([list(p) for p in walls]),
            "paths": {f"{p[0]},{p[1]}": path_to[p] for p in path_to},
            "edges": {f"{p[0]},{p[1]},{d}": v for (p, d), v in edges.items()}
        }, f, indent=2)
    print("\nSaved to maze_full.json")

sys.stdout.flush()
