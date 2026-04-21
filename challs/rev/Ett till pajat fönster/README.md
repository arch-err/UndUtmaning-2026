# Ett till pajat fönster

## Description
> *Berit Beredd's laptop shows a BSOD. Analyze the crash dump to find access codes or useful information.*

**Category:** rev
**Difficulty:** medel
**Files:** [030426-4281-01.dmp](./orig/030426-4281-01.dmp)

## Solution

Windows kernel crash dump contains Driver1.sys which reads encrypted flag from registry, XORs with SIMD, then crashes. Flag survives in XMM14/15 registers in the CONTEXT record.

1. Crash dump (PAGEDU64 small minidump) — bug check code 0x29 (SECURITY_SYSTEM)
2. Driver1.sys loaded at kernel address, uses SIMD (AVX2) to process data
3. Driver reads registry value `\Software\fonster\flag`, converts UTF-16→ASCII via `vpackuswb`, XORs with 4-byte key via `vpxor`
4. Buffer is cleared (`memset 0`) before `KeBugCheckEx` crashes the system
5. **But XMM14/XMM15 still hold the XOR'd flag** — registers are preserved in the CONTEXT record
6. Derive XOR key by assuming plaintext starts with `undut{`: `0xFF 0xFF 0x60 0x48`
7. XOR decode XMM14+XMM15 → flag

```python
xmm14 = bytes.fromhex('8a91043d8b84177888a05720ceca3f3f')
xmm15 = bytes.fromhex('cbca3f7c91915031ce915635ffff6048')
key = bytes([0xff, 0xff, 0x60, 0x48])
flag = bytes([(xmm14+xmm15)[i] ^ key[i%4] for i in range(32)])
print(flag.rstrip(b'\x00'))  # undut{w0w_7h15_w45_4nn0y1n6}
```

## Flag
See [flag.txt](./flag.txt)
