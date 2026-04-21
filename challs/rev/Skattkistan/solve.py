#!/usr/bin/env python3
"""
Skattkistan solver - brute force SHA-256 path search.

The binary hashes the path string (e.g., "hvhvv") with SHA-256
and compares against 4 target hashes. We need to find the path
that produces the treasure hash.

Target hashes (from the binary):
"""
import hashlib
from collections import deque

TARGETS = {
    bytes.fromhex("0482c58b0485e24065d49f615d61d3df8584e1c2517e810ddf161f7876b4b923"): "crossroads",
    bytes.fromhex("6685edeadcd16c21bf56a400651ebf4276941876fb49a0d519a521dd245596aa"): "pearl",
    bytes.fromhex("0eab19775345ef7168cf76989775eebe13392757aba394e57729a7ba730cf7d3"): "necklace",
    bytes.fromhex("c008ee63dca5eca9f3d8fa55a23381505b7f75b37dde838f1d562321ac5b95f1"): "TREASURE",
}

TREASURE_HASH = bytes.fromhex("c008ee63dca5eca9f3d8fa55a23381505b7f75b37dde838f1d562321ac5b95f1")

# BFS - try all paths up to length 39
# At each depth, check if SHA256(path) matches any target
# If treasure found, we're done
# Use items as waypoints to prune if possible

print("Searching for treasure path (BFS)...")
print(f"Max depth: 39, checking SHA256 of path string")

# Start BFS
found_items = {}  # hash -> (path, item_name)

for depth in range(1, 40):
    count = 0
    found_at_depth = False

    # For small depths, try all paths
    if depth <= 25:  # 2^25 = 33M, feasible
        for i in range(2**depth):
            path = ""
            for bit in range(depth):
                if (i >> (depth - 1 - bit)) & 1:
                    path += "v"
                else:
                    path += "h"

            h = hashlib.sha256(path.encode()).digest()

            if h == TREASURE_HASH:
                print(f"\n🎯 TREASURE FOUND at depth {depth}!")
                print(f"Path: {path}")
                print(f"SHA256: {h.hex()}")

                # Now decrypt the flag
                # The flag is XORed with the hash state
                # XOR key is at -0x7ff6(a4) which is the encrypted flag data
                # We need to find this data in the binary
                exit()

            if h in TARGETS:
                item = TARGETS[h]
                if item != "crossroads":
                    print(f"  Depth {depth}: Found {item} with path '{path}'")
                found_at_depth = True

            count += 1
            if count % 10000000 == 0:
                print(f"  Depth {depth}: checked {count}/{2**depth}...")
    else:
        print(f"  Depth {depth}: too many paths (2^{depth}), skipping")
        break

    if not found_at_depth and depth <= 5:
        print(f"  Depth {depth}: no matches in {count} paths")

print("Search complete")
