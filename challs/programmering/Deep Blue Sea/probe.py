#!/usr/bin/env python3
"""Deep Blue Sea - Probe maze structure"""
from pwn import *
import json, time

context.log_level = 'error'

def connect_and_probe(path_str):
    """Try a path, return result type"""
    r = remote("undutmaning-deep.chals.io", 443, ssl=True, sni="undutmaning-deep.chals.io")

    # Read everything until first shark update
    all_data = b""
    for _ in range(20):
        try:
            chunk = r.recv(4096, timeout=2)
            all_data += chunk
            if b'"sharks"' in chunk:
                break
        except:
            pass

    # Send path after first shark update
    time.sleep(0.5)
    r.sendline(path_str.encode('utf-8'))

    # Get response
    time.sleep(2)
    resp = b""
    try:
        resp = r.recv(4096, timeout=5)
    except:
        pass

    r.close()

    resp_str = resp.decode('utf-8', errors='replace')
    if "vägg" in resp_str:
        return "WALL"
    elif "haj" in resp_str:
        return "SHARK"
    elif "vilse" in resp_str:
        return "LOST"
    elif "undut{" in resp_str:
        return "FLAG: " + resp_str
    elif "batteri" in resp_str.lower():
        return "BATTERY: " + resp_str[:100]
    else:
        return "OTHER: " + resp_str[:100]

# Probe single directions from start
print("=== SINGLE STEPS ===")
for d in ["N", "S", "Ö", "V"]:
    result = connect_and_probe(d)
    print(f"  {d}: {result}")

# Probe 2-step combos
print("\n=== 2-STEP PATHS ===")
for d1 in ["S", "Ö", "N", "V"]:
    for d2 in ["S", "Ö", "N", "V"]:
        path = d1 + d2
        result = connect_and_probe(path)
        print(f"  {path}: {result}")

# Try longer south paths
print("\n=== SOUTH EXPLORATION ===")
for length in range(3, 8):
    path = "S" * length
    result = connect_and_probe(path)
    print(f"  {'S'*length}: {result}")
    if result == "WALL":
        break

# Try longer east paths
print("\n=== EAST EXPLORATION ===")
for length in range(3, 8):
    path = "Ö" * length
    result = connect_and_probe(path)
    print(f"  {'Ö'*length}: {result}")
    if result == "WALL":
        break
