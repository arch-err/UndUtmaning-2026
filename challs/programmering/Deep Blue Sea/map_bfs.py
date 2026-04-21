#!/usr/bin/env python3
"""
Deep Blue Sea - BFS maze mapper.
Explore the maze by trying paths and recording wall/open results.
Key insight: sharks are random, so WALL results are definitive, but
SHARK/LOST results mean the path is valid (no walls hit).
"""
from pwn import *
import json, time, sys
from collections import deque

context.log_level = 'error'

# Direction mapping: N=up(-row), S=down(+row), Ö=east(+col), V=west(-col)
DIRS = {'N': (-1, 0), 'S': (1, 0), 'Ö': (0, 1), 'V': (0, -1)}

def try_path(path_str, retries=2):
    """Try a path. Returns: 'WALL', 'OPEN' (lost/shark = no wall hit), or 'FLAG'"""
    for attempt in range(retries):
        try:
            r = remote("undutmaning-deep.chals.io", 443, ssl=True, sni="undutmaning-deep.chals.io")
            all_data = b""
            for _ in range(20):
                try:
                    chunk = r.recv(4096, timeout=2)
                    all_data += chunk
                    if b'"sharks"' in chunk:
                        break
                except:
                    pass

            time.sleep(0.3)
            r.sendline(path_str.encode('utf-8'))

            time.sleep(2)
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
            elif "batteri" in resp_str.lower() or "karta" in resp_str.lower():
                return "SPECIAL: " + resp_str[:200]
            else:
                return "OPEN"  # lost or shark = path is valid (no walls)
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                return f"ERROR: {e}"

# Known results from previous probing:
# Start: N=WALL, V=WALL, S=OPEN, Ö=OPEN
# From S: SÖ=WALL, SV=WALL, SS=OPEN, SN=OPEN(back)
# From Ö: ÖS=WALL, ÖN=WALL, ÖÖ=OPEN, ÖV=OPEN(back)
# ÖÖÖÖÖÖÖ = WALL (7 east), ÖÖÖÖÖÖ = OPEN (6 east)

# So the maze has a corridor going S from start and Ö from start
# S corridor: SS open, going further S seems to work
# Ö corridor: up to 6Ö, then wall at 7Ö. From Ö, can't go N or S.

# Let me explore more systematically using BFS
# Start at (0,0). We know:
# (0,0)->S = open => (1,0) exists
# (0,0)->Ö = open => (0,1) exists
# (0,0)->N = wall
# (0,0)->V = wall

walls = set()  # confirmed walls
open_cells = {(0, 0)}  # confirmed open
edges = {}  # (from_pos, dir) -> True/False (open/wall)

# Pre-load known data
edges[((0,0), 'N')] = False  # wall
edges[((0,0), 'V')] = False  # wall
edges[((0,0), 'S')] = True   # open
edges[((0,0), 'Ö')] = True   # open
open_cells.add((1, 0))
open_cells.add((0, 1))

edges[((1,0), 'Ö')] = False  # SÖ = wall
edges[((1,0), 'V')] = False  # SV = wall
edges[((1,0), 'S')] = True   # SS = open
open_cells.add((2, 0))

edges[((0,1), 'S')] = False  # ÖS = wall
edges[((0,1), 'N')] = False  # ÖN = wall
edges[((0,1), 'Ö')] = True   # ÖÖ = open
open_cells.add((0, 2))

# We know Ö×6 is open, Ö×7 is wall
for i in range(2, 6):
    open_cells.add((0, i))
    edges[((0, i), 'Ö')] = True
open_cells.add((0, 6))
edges[((0, 6), 'Ö')] = False  # 7th Ö hits wall

def pos_after_path(path_str):
    """Calculate position after following a path from (0,0)"""
    r, c = 0, 0
    for ch in path_str:
        dr, dc = DIRS[ch]
        r += dr
        c += dc
    return (r, c)

def path_to_pos(target_r, target_c):
    """Generate a simple path from (0,0) to target using known open paths.
    Uses BFS on known open edges."""
    from collections import deque
    queue = deque([(0, 0, "")])
    visited = {(0, 0)}

    while queue:
        r, c, path = queue.popleft()
        if (r, c) == (target_r, target_c):
            return path

        for d, (dr, dc) in DIRS.items():
            nr, nc = r + dr, c + dc
            if (nr, nc) not in visited and edges.get(((r, c), d)) == True:
                visited.add((nr, nc))
                queue.append((nr, nc, path + d))

    return None  # No known path

# BFS exploration of the maze
frontier = deque()
explored_edges = set()

# Add all unexplored edges from known open cells
for pos in list(open_cells):
    for d in DIRS:
        if ((pos, d)) not in edges:
            frontier.append((pos, d))

print(f"Starting BFS with {len(frontier)} frontier edges")
print(f"Known open cells: {sorted(open_cells)}")

max_probes = 150  # Limit to avoid too many connections
probe_count = 0

while frontier and probe_count < max_probes:
    pos, direction = frontier.popleft()

    if (pos, direction) in edges:
        continue

    # Find path from start to this position
    path_to_here = path_to_pos(pos[0], pos[1])
    if path_to_here is None:
        continue  # Can't reach this position yet

    # Try the path + one step in the direction
    test_path = path_to_here + direction
    result = try_path(test_path)
    probe_count += 1

    dr, dc = DIRS[direction]
    new_pos = (pos[0] + dr, pos[1] + dc)

    if result == "WALL":
        edges[(pos, direction)] = False
        walls.add(new_pos)
        print(f"  [{probe_count}] {test_path} -> WALL (wall at {new_pos})")
    elif result.startswith("FLAG"):
        print(f"\n🚩🚩🚩 FLAG FOUND! Path: {test_path}")
        print(result)
        sys.exit(0)
    elif result.startswith("SPECIAL"):
        print(f"\n⭐ SPECIAL RESPONSE at {new_pos}!")
        print(result)
        edges[(pos, direction)] = True
        open_cells.add(new_pos)
    else:  # OPEN
        edges[(pos, direction)] = True
        open_cells.add(new_pos)
        # Also record reverse direction
        rev = {'N': 'S', 'S': 'N', 'Ö': 'V', 'V': 'Ö'}
        edges[(new_pos, rev[direction])] = True
        print(f"  [{probe_count}] {test_path} -> OPEN (new cell {new_pos})")

        # Add new frontier edges from new_pos
        for d2 in DIRS:
            if (new_pos, d2) not in edges:
                frontier.append((new_pos, d2))

    if probe_count % 20 == 0:
        print(f"\n  --- Status: {len(open_cells)} open cells, {len(walls)} walls, {probe_count} probes ---\n")

# Print the map
print(f"\n=== MAZE MAP ({probe_count} probes) ===")
print(f"Open cells: {len(open_cells)}, Walls: {len(walls)}")

min_r = min(p[0] for p in open_cells | walls)
max_r = max(p[0] for p in open_cells | walls)
min_c = min(p[1] for p in open_cells | walls)
max_c = max(p[1] for p in open_cells | walls)

print(f"Grid: rows {min_r}-{max_r}, cols {min_c}-{max_c}")
print()

for r in range(min_r, max_r + 1):
    row_str = ""
    for c in range(min_c, max_c + 1):
        if (r, c) == (0, 0):
            row_str += "S"  # Start
        elif (r, c) in open_cells:
            row_str += "."
        elif (r, c) in walls:
            row_str += "#"
        else:
            row_str += "?"
    print(f"  {r:3d} |{row_str}|")
