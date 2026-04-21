# Biologiskt mångfald

## Description
> *Crisis in Aquarium #4 — satellite crash scattered 25 fish across the floor. Assign them to 4 tanks following ecological rules.*

**Category:** programmering
**Difficulty:** lätt

## Solution

Constraint satisfaction puzzle. Environment rules + incompatibilities + biomass limits cascade into a nearly forced solution. 79/80 max capacity — razor thin.

1. 4 large predators (size≥6) must go 1-per-tank, environment rules force exact placement:
   - Lionfish→C (only warm), Manta→B (warm/temperate, C taken), BlueShark→A (not brackish), Oscar→D
2. Environment locks chain: Coralfish→C, Angelfish→B (only valid tank), Guppy→B, Pleco→D
3. Tank B fills to exactly 20 (Manta+2×Angelfish+3×Guppy+Goby as detritivore)
4. Detritivore per tank: Catfish→A, Goby→B, Goldfish→C, Pleco+Koi→D
5. BlueShark needs ≥3 small fish (school rule) — fill A with Surgeon, Minnow, Betta×2
6. Remaining fish distributed respecting Puffer≠Surgeon, Betta≠Guppy, Catfish≠Lionfish

## Flag
See [flag.txt](./flag.txt)
> undut{Använde du AI är du inte sigma!}
> *Of course I'm using AI, i won't waste my time on ez programming tasks! 😛*
