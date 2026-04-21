#!/usr/bin/env python3
"""
Undervattensströmmar - LCG Stream Cipher Cracker

The encryption tool (ibtool.c) uses:
- A Linear Congruential Generator: state = (multiplier * state + increment) % modulus
- All params are uint16_t (0-65535)
- XORs 16-bit plaintext words with keystream values
- The plaintext starts with header "IBTOOLBACKUP\x00\x00" (14 bytes = 7 words)

Attack: Known-plaintext on header → recover keystream → crack LCG → decrypt
"""

import struct
from math import gcd
from functools import reduce

# Known header
HEADER = b"IBTOOLBACKUP\x00\x00"

# Read ciphertext
with open("orig/ciphertext", "rb") as f:
    ct_bytes = f.read()

print(f"Ciphertext: {len(ct_bytes)} bytes ({len(ct_bytes)//2} words)")

# Parse as uint16_t little-endian words
ct_words = list(struct.unpack(f"<{len(ct_bytes)//2}H", ct_bytes[:len(ct_bytes)//2*2]))
pt_header_words = list(struct.unpack(f"<{len(HEADER)//2}H", HEADER))

print(f"Header words: {[hex(w) for w in pt_header_words]}")
print(f"CT first words: {[hex(w) for w in ct_words[:7]]}")

# Recover keystream from known plaintext header
ks = [p ^ c for p, c in zip(pt_header_words, ct_words[:7])]
print(f"\nRecovered keystream (first 7 values): {ks}")
print(f"  hex: {[hex(k) for k in ks]}")

# Crack LCG parameters using known consecutive outputs
# LCG: ks[i+1] = (a * ks[i] + b) % m
#
# Method: Use differences to find modulus via GCD
# d[i] = ks[i+1] - ks[i]
# d[i+1] = a * d[i] (mod m)
# So: d[i+2]*d[i] - d[i+1]^2 ≡ 0 (mod m)

d = [ks[i+1] - ks[i] for i in range(len(ks)-1)]
print(f"\nDifferences: {d}")

# Compute d[i+2]*d[i] - d[i+1]^2 for all valid i
zeroes_mod_m = []
for i in range(len(d) - 2):
    val = d[i+2] * d[i] - d[i+1] * d[i+1]
    zeroes_mod_m.append(abs(val))
    print(f"  d[{i+2}]*d[{i}] - d[{i+1}]^2 = {val}")

# GCD of all these gives us a multiple of m (hopefully m itself)
modulus_candidate = reduce(gcd, zeroes_mod_m)
print(f"\nGCD of zero-mod-m values: {modulus_candidate}")

# Factor out small primes to find the actual modulus
# The modulus should be <= 65535 (uint16_t)
# Let's also check if the candidate needs to be divided down
m = modulus_candidate
print(f"Modulus candidate: {m}")

# If modulus is too large, try dividing by small factors
if m > 65535:
    for div in range(2, 1000):
        while m % div == 0 and m // div > max(ks) and m // div <= 65535:
            m = m // div
    print(f"Adjusted modulus: {m}")

# Verify: all keystream values should be < modulus
print(f"Max keystream value: {max(ks)}, modulus: {m}")
assert all(k < m for k in ks), "Keystream values exceed modulus!"

# Recover multiplier: a = d[1] * inverse(d[0]) mod m
# Or: a = (ks[2] - ks[1]) * inverse(ks[1] - ks[0]) mod m
# But we need modular inverse, which requires gcd(d[0], m) = 1

def modinv(a, m):
    """Extended GCD to find modular inverse"""
    a = a % m
    g, x, _ = extended_gcd(a, m)
    if g != 1:
        return None  # No inverse
    return x % m

def extended_gcd(a, b):
    if a == 0:
        return b, 0, 1
    g, x, y = extended_gcd(b % a, a)
    return g, y - (b // a) * x, x

# Try to find multiplier from consecutive differences
# d[i+1] = a * d[i] mod m
for i in range(len(d) - 1):
    inv = modinv(d[i] % m, m)
    if inv is not None:
        a_candidate = (d[i+1] * inv) % m
        print(f"\nFrom d[{i}]→d[{i+1}]: multiplier candidate = {a_candidate}")

        # Verify with other pairs
        valid = True
        for j in range(len(d) - 1):
            if (a_candidate * d[j]) % m != d[j+1] % m:
                valid = False
                break
        if valid:
            a = a_candidate
            print(f"  ✓ Verified across all differences!")
            break
        else:
            print(f"  ✗ Failed verification")

# Recover increment: b = (ks[1] - a * ks[0]) % m
b = (ks[1] - a * ks[0]) % m
print(f"\nLCG Parameters:")
print(f"  multiplier (a) = {a}")
print(f"  increment  (b) = {b}")
print(f"  modulus    (m) = {m}")

# Verify: generate keystream and check it matches
state = ks[0]  # First keystream value is the first output
# But wait - what's the seed? The seed is the initial state BEFORE the first generate call
# generate_next_keystream updates state THEN returns it
# So: ks[0] = (a * seed + b) % m
# seed = (ks[0] - b) * inverse(a) % m
seed_inv = modinv(a, m)
if seed_inv:
    seed = ((ks[0] - b) * seed_inv) % m
    print(f"  seed           = {seed}")

# Verify by regenerating keystream
print(f"\nVerification:")
state = seed
for i in range(7):
    state = (a * state + b) % m
    match = "✓" if state == ks[i] else "✗"
    print(f"  ks[{i}] = {state} (expected {ks[i]}) {match}")

# Decrypt the full ciphertext!
print(f"\n=== DECRYPTING ===")
state = seed
plaintext_words = []
for ct_word in ct_words:
    state = (a * state + b) % m
    pt_word = ct_word ^ state
    plaintext_words.append(pt_word)

# Convert words back to bytes
plaintext = struct.pack(f"<{len(plaintext_words)}H", *plaintext_words)

# Handle odd byte if present
if len(ct_bytes) % 2 == 1:
    state = (a * state + b) % m
    last_byte = ct_bytes[-1] ^ (state & 0xFF)
    plaintext += bytes([last_byte])

print(f"Decrypted {len(plaintext)} bytes")
print(f"\nHeader check: {plaintext[:14]}")
print(f"Header valid: {plaintext[:14] == HEADER}")

# Save decrypted output
with open("decrypted.bin", "wb") as f:
    f.write(plaintext)

# Try to display as text (skip header)
payload = plaintext[14:]
print(f"\n=== PAYLOAD (after header) ===")
try:
    text = payload.decode('utf-8', errors='replace')
    print(text[:500])
except:
    print(f"Binary data, first 100 bytes hex:")
    print(payload[:100].hex())

# Also check for flag
import re
flag_match = re.search(rb'undut\{[^}]+\}', plaintext)
if flag_match:
    print(f"\n🚩 FLAG FOUND: {flag_match.group().decode()}")
else:
    print("\nNo flag pattern found in decrypted text directly.")
    print("Checking file type of payload...")
