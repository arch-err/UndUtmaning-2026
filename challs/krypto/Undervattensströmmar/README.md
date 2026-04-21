# Undervattensströmmar

## Description
> *Harriet found a USB stick marked "Viktigt!!!" with bite marks. Two files survived: the encryption tool source and a ciphertext.*

**Category:** krypto
**Difficulty:** svår

## Solution

Known-plaintext attack on LCG stream cipher. Header gives keystream, GCD trick cracks parameters, XOR decrypts to gzipped tar with flag.

1. `ibtool.c` is a stream cipher using a **Linear Congruential Generator** (LCG) with uint16_t parameters
2. Encryption XORs 16-bit plaintext words with LCG keystream: `state = (a * state + b) % m`
3. Input files must start with header `IBTOOLBACKUP\x00\x00` (14 bytes = 7 words) — and the header IS encrypted
4. XOR first 7 ciphertext words with known header → 7 keystream values
5. Crack LCG using consecutive differences: `d[i+2]*d[i] - d[i+1]^2 ≡ 0 (mod m)`, GCD gives modulus
6. Recover multiplier via modular inverse of differences, increment from first two values
7. **Parameters:** multiplier=35, increment=10088, modulus=22661, seed=22572
8. Decrypt → strip header → gunzip → untar → flag

## Flag
See [flag.txt](./flag.txt)
