# Infekterad BIOS

## Description
> *Harriet found a submarine wreck with a computer containing a flash chip with UEFI firmware. A suspicious file is embedded in the firmware — investigate it.*

**Category:** krypto
**Difficulty:** svår
**Files:** [bin.efi](./orig/bin.efi)

## Solution

UEFI runtime driver that hooks `SetVariable`, finds ntoskrnl via LSTAR MSR, and XOR-decrypts the flag using PE header bytes as key.

1. `bin.efi` is a PE32+ UEFI runtime driver that hooks the `SetVariable` runtime service
2. When `SecureBoot` variable is written, it triggers the payload:
   - Reads MSR `0xC0000082` (LSTAR) to find `KiSystemCall64`
   - Scans backwards in 0x1000 increments for PE header (`MZ` + `PE\0\0`) → ntoskrnl base
   - Resolves `ZwCreateFile` / `ZwWriteFile` exports (names stored NOT-encoded to avoid `strings`)
3. Key derivation: `key[i] = ntoskrnl_base_bytes[i % 5] ^ 0x22`
   - Every PE starts with DOS stub `4D 5A 90 00 03` → key is `0x6f 0x78 0xb2 0x22 0x21`
4. 25 bytes of embedded ciphertext XOR'd with repeating key → flag
5. No execution needed — key is deterministic from the PE standard

```python
ntoskrnl_bytes = [0x4d, 0x5a, 0x90, 0x00, 0x03]
key = [b ^ 0x22 for b in ntoskrnl_bytes]
enc = [0x1a, 0x16, 0xd6, 0x57, 0x55, 0x14, 0x2d, 0xd7, 0x44, 0x48,
       0x3a, 0x16, 0xd6, 0x57, 0x55, 0x2c, 0x10, 0xd3, 0x4e, 0x4d,
       0x0a, 0x16, 0xd5, 0x47, 0x5c]
flag = ''.join(chr(enc[i] ^ key[i % 5]) for i in range(25))
print(flag)  # undut{UefiUndutChallenge}
```

## Flag
See [flag.txt](./flag.txt)
