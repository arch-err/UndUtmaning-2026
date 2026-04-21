#!/usr/bin/env python3
"""Deep Blue Sea - Recon: connect and observe the protocol"""
from pwn import *
import json, time

context.log_level = 'info'

r = remote("undutmaning-deep.chals.io", 443, ssl=True, sni="undutmaning-deep.chals.io")

# Read everything for ~20 seconds to understand the protocol
start = time.time()
data = b""
while time.time() - start < 25:
    try:
        chunk = r.recv(4096, timeout=2)
        if chunk:
            data += chunk
            print(f"[{time.time()-start:.1f}s] Got {len(chunk)} bytes")
            print(chunk.decode('utf-8', errors='replace'))
            print("---")
    except:
        pass

# Try sending a simple path and see what happens
print("\n=== SENDING TEST PATH ===")
r.sendline(b"N")
time.sleep(3)
try:
    response = r.recv(4096, timeout=5)
    print(f"Response: {response.decode('utf-8', errors='replace')}")
except:
    print("No response")

r.close()
