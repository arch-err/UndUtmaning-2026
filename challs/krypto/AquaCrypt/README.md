# AquaCrypt

## Description
> *Harriet found a web file-sharing service on CASCADA's network. Some files have interesting names, but she needs help accessing them.*

**Category:** krypto
**Difficulty:** medel
**Link:** [https://undutmaning-aquacrypt.chals.io](https://undutmaning-aquacrypt.chals.io)

## Solution

`robots.txt` leaks an admin panel with source download. The "proprietary 128-bit crypto" is RSA with a 128-bit modulus and e=3 — trivially factorable.

1. `robots.txt` reveals `/admin` endpoint
2. Admin panel has "Download Server Config" link → full Flask app source
3. Obfuscated verification function (base64+gzip+length encoding) decodes to RSA signature check
4. RSA public key: 128-bit n, e=3
5. `n = 16016280254797801469 × 14644073284032460883`
6. Compute private key d, forge PKCS#1 v1.5 signature for filename "flag"
7. Download flag file with forged signature

```python
import base64
n = 234543581788861099913565055818142437127
p, q = 16016280254797801469, 14644073284032460883
d = pow(3, -1, (p-1)*(q-1))
message = b'flag'
padded = b'\x00\x01' + b'\xff' * 9 + b'\x00' + message
sig = pow(int.from_bytes(padded, 'big'), d, n).to_bytes(16, 'big')
print(base64.b64encode(sig).decode())  # Use as signature parameter
```

## Flag
See [flag.txt](./flag.txt)
