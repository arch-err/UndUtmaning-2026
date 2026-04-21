#!/usr/bin/env python3
"""
Deep Blue Sea - Use shark positions to map the maze.
Sharks only exist on open cells, so their positions reveal the maze structure.
Collect many snapshots to build a complete picture.
"""
from pwn import *
import json, time, re

context.log_level = 'error'

all_positions = set()
snapshots = 0

# Collect shark data from multiple connections in parallel-ish
print("Collecting shark position data...")
for conn_num in range(8):  # 8 connections
    try:
        r = remote("undutmaning-deep.chals.io", 443, ssl=True, sni="undutmaning-deep.chals.io")
        data = b""
        start = time.time()
        while time.time() - start < 45:  # 45 seconds per connection = ~7 updates
            try:
                chunk = r.recv(4096, timeout=3)
                data += chunk
            except:
                pass
        r.close()

        # Parse shark positions
        for match in re.finditer(rb'"sharks":\s*(\[\[.*?\]\])', data):
            try:
                sharks = json.loads(match.group(1))
                for pos in sharks:
                    all_positions.add((pos[0], pos[1]))
                snapshots += 1
            except:
                pass

        print(f"  Connection {conn_num+1}: {len(all_positions)} unique positions, {snapshots} snapshots")
    except Exception as e:
        print(f"  Connection {conn_num+1}: error - {e}")

print(f"\nTotal: {len(all_positions)} unique shark positions from {snapshots} snapshots")

# Build the grid
if not all_positions:
    print("No data collected!")
    exit(1)

min_r = min(p[0] for p in all_positions)
max_r = max(p[0] for p in all_positions)
min_c = min(p[1] for p in all_positions)
max_c = max(p[1] for p in all_positions)

print(f"Grid bounds: rows {min_r}-{max_r}, cols {min_c}-{max_c}")
print(f"Grid size: {max_r - min_r + 1} x {max_c - min_c + 1}")

# Visualize
print(f"\nMaze map (. = shark visited = open, # = never visited = likely wall):")
print(f"     ", end="")
for c in range(min_c, max_c + 1):
    print(f"{c%10}", end="")
print()

open_count = 0
wall_count = 0
for r in range(min_r, max_r + 1):
    print(f"  {r:2d} |", end="")
    for c in range(min_c, max_c + 1):
        if (r, c) in all_positions:
            print(".", end="")
            open_count += 1
        else:
            print("#", end="")
            wall_count += 1
    print("|")

print(f"\nOpen cells: {open_count}, Likely walls: {wall_count}")

# Save data for solver
with open("maze_data.json", "w") as f:
    json.dump({
        "open_cells": sorted([list(p) for p in all_positions]),
        "min_r": min_r, "max_r": max_r,
        "min_c": min_c, "max_c": max_c,
        "snapshots": snapshots
    }, f)
print("\nSaved to maze_data.json")
