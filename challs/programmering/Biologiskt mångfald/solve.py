#!/usr/bin/env python3
"""
Biologiskt mångfald — Constraint satisfaction: assign 25 fish to 4 tanks.

Tanks:
  A: Deep sea (salt, cold, dark)
  B: Temperate (salt, temperate)
  C: Coral (salt, warm)
  D: Brackish (brackish, temperate)

Max biomass per tank: 20
Total fish biomass: 79 (max capacity: 80)

Key forced assignments:
- 4 large predators (size≥6): BlueShark(8), Manta(7), Lionfish(6), Oscar(7) — one per tank
- Lionfish → C (only warm)
- Manta → B or C → B (C taken by Lionfish)
- Oscar → A or D (brackish or dark)
- BlueShark → not D (not brackish), not C (Lionfish), not B (Manta) → A
- Oscar → D (A taken by BlueShark)

Then environment locks:
- Coralfish → C (warm+coral)
- Angelfish → B only (not cold A, not with Lionfish C, not with Oscar D)
- Guppy → B (temperate, not with Oscar D, not with Lionfish C)
- Pleco → D (not high salt)
- Koi → not A (cold)
"""

import requests
import json

# The solution worked out by hand:
assignments = {
    # Large predators (one per tank, forced)
    "BlueShark": "TankA",
    "Manta": "TankB",
    "Lionfish": "TankC",
    "Oscar": "TankD",

    # Environment-forced
    "Coralfish": "TankC",
    "Angelfish_1": "TankB",
    "Angelfish_2": "TankB",
    "Guppy_1": "TankB",
    "Guppy_2": "TankB",
    "Guppy_3": "TankB",
    "Pleco": "TankD",

    # Detritivores (one per tank)
    "Catfish": "TankA",    # detritivore for A
    "Goby": "TankB",       # detritivore for B (2 units, fits exactly)
    "Goldfish": "TankC",   # detritivore for C
    "Koi": "TankD",        # detritivore for D (not cold, OK)

    # Fill remaining (respect incompatibilities + BlueShark school rule)
    # Tank A needs ≥3 small fish (size≤3) for BlueShark rule — Catfish counts as 1
    "Surgeon": "TankA",    # size 3
    "Minnow": "TankA",     # size 3
    "Betta_1": "TankA",    # size 2
    "Betta_2": "TankA",    # size 2

    # Tank C: fill remaining capacity (7 left after Lionfish+Coralfish+Goldfish=13)
    "Clown": "TankC",      # size 3
    "Puffer": "TankC",     # size 2 (Puffer≠Surgeon, Surgeon in A ✓)
    "Swordtail": "TankC",  # size 2

    # Tank D: remaining
    "Tetra_1": "TankD",    # size 2
    "Tetra_2": "TankD",    # size 2
    "Tetra_3": "TankD",    # size 2
}

# Verify biomass
tanks = {"TankA": [], "TankB": [], "TankC": [], "TankD": []}
sizes = {
    "BlueShark": 8, "Manta": 7, "Lionfish": 6, "Oscar": 7,
    "Angelfish_1": 4, "Angelfish_2": 4, "Koi": 4, "Goldfish": 4,
    "Clown": 3, "Surgeon": 3, "Coralfish": 3, "Minnow": 3,
    "Puffer": 2, "Catfish": 2, "Betta_1": 2, "Betta_2": 2,
    "Swordtail": 2, "Goby": 2, "Pleco": 2,
    "Guppy_1": 1, "Guppy_2": 1, "Guppy_3": 1,
    "Tetra_1": 2, "Tetra_2": 2, "Tetra_3": 2,
}

for fish, tank in assignments.items():
    tanks[tank].append((fish, sizes[fish]))

print("=== TANK ASSIGNMENTS ===")
for tank, fish_list in tanks.items():
    total = sum(s for _, s in fish_list)
    names = [f"{n}({s})" for n, s in fish_list]
    print(f"{tank}: {' + '.join(names)} = {total}/20")

print(f"\nTotal fish: {len(assignments)}")
print(f"Total biomass: {sum(sizes.values())}")

# Submit
print("\n=== SUBMITTING ===")
r = requests.post("https://undutmaning-mangfald.chals.io/verify",
                   json={"assignments": assignments},
                   headers={"Content-Type": "application/json"})
print(f"Status: {r.status_code}")
data = r.json()
print(json.dumps(data, indent=2, ensure_ascii=False))

if data.get("ok"):
    print(f"\n🚩 FLAG: {data['flag']}")
else:
    print(f"\n❌ Error: {data.get('error')}")
