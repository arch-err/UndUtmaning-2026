# Manifest deepthingy

## Description
> *Instruktioner för hur du ansluter till utmaningstjänster hittar du på [informationssidan](info#anslutning).*

**Category:** rev
**Difficulty:** lätt

## Solution

Reverse engineered the CASCADA Manual Server binary. Protocol: TLS on port 443, challenge-response auth using XOR + ROL8 transform with embedded SECRET_KEY, then encrypted command/response loop using a keystream derived from the 8-byte challenge XOR'd with a reconstructed manifest (4688 bytes, deobfuscated from MANIFEST_OBF using ROR8 + XOR). Commands: `LIST` and `REQUEST <file>`. Flag was hidden in `Städregelemente (sanitetsutrymmen).md` — the toilet cleaning manual.

See [solve2.py](./solve2.py) for the full client.

## Flag
See [flag.txt](./flag.txt)
