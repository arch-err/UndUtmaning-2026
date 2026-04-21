#!/usr/bin/env python3
"""Deep Blue Sea - Parallel shark-aware solver"""
from PIL import Image
import numpy as np
import json, time, sys, os
from collections import deque
from pwn import *
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

context.log_level = 'error'

# Parse maze
img = Image.open('lab-map.png').convert('L')
arr = np.array(img).astype(int)
CELL = 28

maze = []
for r in range(31):
    row = []
    for c in range(31):
        py = r * CELL + CELL // 2
        px = c * CELL + CELL // 2
        region = arr[max(0,py-6):py+7, max(0,px-6):px+7]
        avg = region.mean()
        row.append(1 if avg > 100 else 0)
    maze.append(row)

START = (1, 1)
BATTERY = (29, 29)
DIRS = [('S', 1, 0), ('N', -1, 0), ('Ö', 0, 1), ('V', 0, -1)]

def bfs(start, end, blocked):
    queue = deque([(start, "")])
    visited = {start}
    while queue:
        pos, path = queue.popleft()
        if pos == end:
            return path
        for d_name, dr, dc in DIRS:
            nr, nc = pos[0]+dr, pos[1]+dc
            if 0 <= nr < 31 and 0 <= nc < 31 and maze[nr][nc] and (nr, nc) not in visited and (nr, nc) not in blocked:
                visited.add((nr, nc))
                queue.append(((nr, nc), path + d_name))
    return None

flag_found = threading.Event()
attempt_count = [0]
lock = threading.Lock()

def solve_attempt(attempt_id):
    if flag_found.is_set():
        return None
    try:
        r = remote('undutmaning-deep.chals.io', 443, ssl=True, sni='undutmaning-deep.chals.io')
        
        data = b""
        start_t = time.time()
        while time.time() - start_t < 12:
            try:
                chunk = r.recv(4096, timeout=3)
                data += chunk
                if b'"sharks"' in chunk:
                    break
            except:
                pass
        
        sharks = set()
        text = data.decode('utf-8', errors='replace')
        for line in text.split('\n'):
            if '"sharks"' in line:
                try:
                    idx = line.index('{')
                    d = json.loads(line[idx:])
                    for s in d['sharks']:
                        sharks.add(tuple(s))
                except:
                    pass
        
        if not sharks or flag_found.is_set():
            r.close()
            return None
        
        fwd = bfs(START, BATTERY, sharks)
        ret = bfs(BATTERY, START, sharks) if fwd else None
        
        if not fwd or not ret:
            r.close()
            return None
        
        full = fwd + ret
        r.sendline(full.encode('utf-8'))
        time.sleep(0.5)
        
        resp = b""
        try:
            resp = r.recv(8192, timeout=10)
        except:
            pass
        r.close()
        
        resp_text = resp.decode('utf-8', errors='replace')
        
        with lock:
            attempt_count[0] += 1
            n = attempt_count[0]
        
        if 'undut{' in resp_text:
            flag_found.set()
            return ("FLAG", resp_text, n)
        elif 'vägg' in resp_text:
            return ("WALL", resp_text[:100], n)
        elif 'haj' in resp_text:
            if n % 20 == 0:
                print(f"[{n}] Shark hit. Path={len(full)} steps. Still trying...", flush=True)
            return ("SHARK", None, n)
        elif 'batteri' in resp_text.lower() or 'grattis' in resp_text.lower():
            return ("SPECIAL", resp_text, n)
        else:
            return ("OTHER", resp_text[:200], n)
    except Exception as e:
        return ("ERROR", str(e), -1)

print(f"Starting parallel solver with 8 workers...", flush=True)
print(f"Maze: 31x31, {sum(sum(r) for r in maze)} open cells", flush=True)
print(f"Start: {START}, Battery: {BATTERY}", flush=True)

with ThreadPoolExecutor(max_workers=8) as executor:
    batch = 0
    while not flag_found.is_set() and batch < 100:
        futures = [executor.submit(solve_attempt, batch*8 + i) for i in range(8)]
        for f in as_completed(futures):
            result = f.result()
            if result and result[0] == "FLAG":
                print(f"\n🚩🚩🚩 FLAG on attempt {result[2]}!", flush=True)
                print(result[1], flush=True)
                flag_found.set()
                # Write flag to file
                with open('FLAG.txt', 'w') as fl:
                    fl.write(result[1])
                os._exit(0)
            elif result and result[0] == "WALL":
                print(f"WALL HIT: {result[1]}", flush=True)
            elif result and result[0] == "SPECIAL":
                print(f"SPECIAL: {result[1]}", flush=True)
            elif result and result[0] not in ("SHARK", "ERROR", None):
                print(f"OTHER: {result}", flush=True)
        batch += 1

print(f"Done. Total attempts: {attempt_count[0]}", flush=True)
