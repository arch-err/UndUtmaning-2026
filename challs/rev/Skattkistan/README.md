# Skattkistan

## Description
> *AmigaOS m68k text adventure with SHA-256 maze generation.*

**Category:** rev
**Difficulty:** svår
**Files:** [skattkistan](./orig/skattkistan)

## Solution

AmigaOS m68k binary — text adventure maze with SHA-256 path verification, brute-forced from waypoints.

1. Binary computes SHA256(SHA256(path)) at each step and compares with 4 target hashes
2. Found waypoints: crossroads→'h' (depth 1), pearl→'hhv' (depth 3), necklace→'hhvvhvvhhhv' (depth 11)
3. Brute-forced from necklace prefix — treasure at depth 38 (67M paths from necklace)
4. Path: `hhvvhvvhhhvvvhhvhvvvhhvhvhhhvvvhhvhhhv`
5. Flag = encrypted_data XOR SHA256(path)

## Flag
See [flag.txt](./flag.txt)
