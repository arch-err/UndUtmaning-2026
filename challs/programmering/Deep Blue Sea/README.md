# Deep Blue Sea

## Description
> *Instruktioner för hur du ansluter till utmaningstjänster hittar du på [informationssidan](info#anslutning).*

**Category:** programmering
**Difficulty:** medel
**Files:** See [orig/](./orig/)

## Solution

Navigate a 31x31 maze (parsed from `lab-map.png`) to collect a battery and return to the entrance, while avoiding randomly-positioned sharks that update every 6 seconds.

### Key Insight: Two-Phase Approach

The challenge gives you NEW shark positions when you reach the battery corner. This means:
1. **Phase 1:** Send forward path (avoiding initial sharks) → reach battery
2. **Phase 2:** Receive fresh shark positions → send return path (avoiding new sharks)

This halves the exposure window vs submitting a full round-trip path, dramatically improving success odds.

### Steps

1. **Parse the maze:** Download `lab-map.png` from CTFd. The image is 868x868 pixels with a 31x31 grid (868/31 = 28px per cell). Downscale to 31x31 → pixel-perfect maze.
2. **Validate with shark positions:** Shark coordinates from the server map directly to the 31x31 grid. All 41 observed shark positions confirmed as open cells (0 mismatches).
3. **Connect via TLS:** `remote('undutmaning-deep.chals.io', 443, ssl=True, sni=...)`
4. **Phase 1:** Receive shark update → BFS from (1,1) to (29,29) avoiding sharks → submit forward path → battery found
5. **Phase 2:** Receive new shark update → BFS from (29,29) to (1,1) → submit return path
6. **Flag in response**

### Tools

- Python + pwntools for TLS connection
- PIL for image parsing (downscale to 31x31)
- BFS pathfinding with shark avoidance
- Automated retry loop (sharks are random, ~5% cell occupancy)

## Flag
See [flag.txt](./flag.txt)
