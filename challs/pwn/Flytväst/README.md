# Flytväst

## Description
> *Life vest dispenser system. Enter measurements, get a vest. But if you want the special RGB+kazoo vest, you need to get INTO the system.*

**Category:** pwn
**Difficulty:** medel
**Connection:** `undutmaning-flytvast.chals.io` (TLS/SNI, port 443)
**Files:** See [orig/](./orig/)

## Solution

Stack buffer overflow with canary bypass. Float array position 4 overwrites the loop counter, allowing an index skip past the canary to overwrite the return address with `print_flag`.

1. Binary reads "measurements" as floats into a stack array with **no bounds check**
2. Position 4 in the array overlaps the counter variable at `rbp-0x10`
3. Writing a denormalized float with bits `0x00000009` sets counter to 10 after increment
4. This skips positions 5-9 (including the stack canary at positions 6-7)
5. Next writes land at positions 10-11 = return address (`rbp+0x08`)
6. Write `print_flag` address (0x4012b6) as a denorm float, high bytes as 0.0
7. Function returns to `print_flag` → flag printed

Key insight: `cvtsd2ss` preserves denormalized floats, so `1.26e-44` (float bits = 9) works as the counter overwrite value.

## Flag
See [flag.txt](./flag.txt)
