#!/usr/bin/env python3
"""Deep Blue Sea - Explore: try submitting paths to understand the protocol"""
from pwn import *
import json, time

context.log_level = 'error'

def connect_and_try(path_str):
    r = remote("undutmaning-deep.chals.io", 443, ssl=True, sni="undutmaning-deep.chals.io")

    # Read intro
    intro = r.recvuntil(b"informerar:\n", timeout=10)
    sharks1 = r.recvline(timeout=10)
    print(f"First shark update received")

    # Send path
    print(f"Sending path: {path_str[:50]}...")
    r.sendline(path_str.encode())

    # Collect all responses
    time.sleep(8)
    try:
        response = r.recv(65536, timeout=10)
        print(f"Response ({len(response)} bytes):")
        print(response.decode('utf-8', errors='replace'))
    except:
        print("No response / timeout")

    r.close()
    return sharks1

# Test 1: Single step south
print("=== TEST 1: Single step S ===")
connect_and_try("S")

print("\n=== TEST 2: Long south path ===")
connect_and_try("SSSSSSSSSS")

print("\n=== TEST 3: Long south-east path ===")
connect_and_try("SÖSÖSÖSÖSÖSÖSÖSÖSÖSÖ")

print("\n=== TEST 4: Just wait (empty) ===")
connect_and_try("")
