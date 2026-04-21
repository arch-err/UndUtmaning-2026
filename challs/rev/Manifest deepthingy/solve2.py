#!/usr/bin/env python3
"""
Solver for "Manifest deepthingy" CTF challenge
CASCADA Manual Server v2.2 - reverse engineered protocol client

Protocol:
  1. Server sends banner (raw text, newline terminated)
  2. Server sends challenge (type=1, 8 bytes random)
  3. Client sends transformed challenge (type=2, 8 bytes)
  4. Server sends AUTH OK (type=3) or error (type=0xFFFF) — PLAINTEXT
  5. Loop:
     a. Client sends command (type=0x100) — ENCRYPTED
     b. Server decrypts it, processes, sends response (type=0x101) — ENCRYPTED
     
  Encryption: apply_keystream uses challenge[i&7] XOR manifest[(offset+i) % manifest_len]
  The manifest_offset is a shared counter incremented for BOTH received and sent encrypted data.
  
  In handle_client:
  - After recv, if pkt_len > 0: apply_keystream on received data (decrypts it)  
  - Before sending response: apply_keystream on response data (encrypts it)
  
  So client must:
  - ENCRYPT commands before sending (same keystream)
  - DECRYPT responses after receiving
"""

import socket
import ssl
import struct

HOST = "undutmaning-manifest.chals.io"
PORT = 443

SECRET_KEY = bytes.fromhex("a5b37c22914e5fd2")

def rol8(val, shift):
    shift = shift & 7
    val = val & 0xff
    return ((val << shift) | (val >> (8 - shift))) & 0xff

def ror8(val, shift):
    shift = shift & 7
    val = val & 0xff
    return ((val >> shift) | (val << (8 - shift))) & 0xff

def transform_challenge(challenge: bytes) -> bytes:
    result = bytearray(8)
    for i in range(8):
        tmp = challenge[i] ^ SECRET_KEY[i]
        rot = i % 3
        tmp = rol8(tmp, rot)
        if i & 1:
            tmp = (~tmp) & 0xff
        result[i] = tmp
    return bytes(result)

def reconstruct_manifest():
    import os
    binary_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orig", "server")
    with open(binary_path, 'rb') as f:
        f.seek(0x5020)
        manifest_obf = f.read(0x1250)
    
    seed1 = 0xa5
    seed2 = 0x1f
    manifest = bytearray(len(manifest_obf))
    for i in range(len(manifest_obf)):
        obf_byte = manifest_obf[i]
        tmp = ((i * seed2) & 0xff) ^ obf_byte
        tmp2 = ror8(tmp, i % 7)
        result = tmp2 ^ seed1
        manifest[i] = result
    return bytes(manifest)

class CascadaClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
        self.manifest = reconstruct_manifest()
        self.manifest_len = len(self.manifest)
        self.manifest_offset = 0  # shared offset for encryption state
        self.challenge = None
        
    def connect(self):
        raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raw.settimeout(10)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        self.sock = ctx.wrap_socket(raw, server_hostname=self.host)
        self.sock.connect((self.host, self.port))
        
    def recv_all(self, n):
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Connection closed")
            data += chunk
        return data
    
    def send_all(self, data):
        self.sock.sendall(data)
        
    def send_packet(self, pkt_type, payload, payload_len):
        header = struct.pack("!HH", pkt_type, payload_len)
        self.send_all(header)
        if payload_len > 0:
            self.send_all(payload[:payload_len])
            
    def recv_packet(self):
        type_data = self.recv_all(2)
        len_data = self.recv_all(2)
        pkt_type = struct.unpack("!H", type_data)[0]
        pkt_len = struct.unpack("!H", len_data)[0]
        payload = b""
        if pkt_len > 0:
            payload = self.recv_all(pkt_len)
        return pkt_type, payload, pkt_len
    
    def apply_keystream(self, data):
        """Apply keystream XOR to data, updating shared offset."""
        result = bytearray(data)
        for i in range(len(data)):
            key_byte = 0
            if self.manifest is not None and self.manifest_len > 0:
                idx = (self.manifest_offset + i) % self.manifest_len
                key_byte = self.manifest[idx]
            challenge_byte = self.challenge[i & 7]
            stream_byte = key_byte ^ challenge_byte
            result[i] ^= stream_byte
        self.manifest_offset += len(data)
        return bytes(result)
    
    def handshake(self):
        # Read banner
        banner = b""
        while not banner.endswith(b"\n"):
            banner += self.sock.recv(4096)
        print(f"[*] Banner: {banner.decode().strip()}")
        
        # Receive challenge
        pkt_type, challenge, pkt_len = self.recv_packet()
        assert pkt_type == 1 and pkt_len == 8
        self.challenge = challenge
        print(f"[*] Challenge: {challenge.hex()}")
        
        # Send response
        response = transform_challenge(challenge)
        print(f"[*] Response: {response.hex()}")
        self.send_packet(2, response, 8)
        
        # Receive auth result (PLAINTEXT - no encryption)
        pkt_type, auth_data, auth_len = self.recv_packet()
        print(f"[*] Auth: type={pkt_type}, data={auth_data}")
        
        if pkt_type == 0xFFFF:
            print("[-] AUTH FAILED!")
            return False
        
        # AUTH OK is type=3, plaintext. DO NOT decrypt it.
        # The manifest_offset stays at 0.
        print(f"[+] Authenticated!")
        return True
    
    def send_command(self, cmd: str):
        """Encrypt and send a command."""
        cmd_bytes = cmd.encode()
        encrypted = self.apply_keystream(cmd_bytes)
        self.send_packet(0x100, encrypted, len(encrypted))
        
    def recv_response(self):
        """Receive and decrypt a response."""
        pkt_type, payload, pkt_len = self.recv_packet()
        if pkt_len > 0:
            decrypted = self.apply_keystream(payload)
            return pkt_type, decrypted
        return pkt_type, b""
    
    def list_files(self):
        self.send_command("LIST")
        pkt_type, data = self.recv_response()
        print(f"[*] LIST response (type={pkt_type}):")
        text = data.decode('utf-8', errors='replace')
        print(text)
        return text.strip().split('\n')
    
    def get_file(self, filename):
        self.send_command(f"REQUEST {filename}")
        pkt_type, data = self.recv_response()
        return data

def solve():
    client = CascadaClient(HOST, PORT)
    client.connect()
    
    if not client.handshake():
        return
    
    # List files
    files = client.list_files()
    
    # Download each file
    for f in files:
        f = f.strip()
        if not f:
            continue
        print(f"\n[*] Downloading: {f}")
        content = client.get_file(f)
        try:
            print(content.decode('utf-8'))
        except:
            print(content.hex())
    
    client.sock.close()
    print("\n[*] Done!")

if __name__ == "__main__":
    solve()
