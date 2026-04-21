# På botten

## Description

> *Inte långt från CASCADA, där havet i området är som djupast, ligger en interkontinental kommunikationskabel på botten. CASCADAs dykexpert, Mildred Milwaukee, får i uppdrag att inspektera kabeln och försöka ta reda på om hjälp är på väg. Hon ansluter sin kabellyssnare och får fram en signal som hon har svårt att tolka. Hon kallar på hjälp via radio...*
>
> *Tyvärr är det si och så med GPS-signalen här nere på botten, så det kanske kan vara svårt att hitta Mildred. Du lyckas bara få en ungefärlig position, så det enda du har tillgång till när du ger dig iväg är en adress: `challs.undutmaning.se`. Men du behöver en mer exakt position (port) också. Kan du lista ut var hon är och hjälpa henne att tolka signalen?*
>
> *Den här utmaningen kör inte på CTFd-plattformen. Mer utförliga instruktioner för hur du ansluter till utmaningstjänster hittar du på [informationssidan](info#anslutning-other).*

**Category:** misc / forensik
**Points:** 100
**Difficulty:** lätt (easy)

### Provided hints

1. `xyzxyzxdyzjxyzxuyzxypzetxyäzrxyzpxoyzxrteyzxyzxyznxyz`
2. `ÅTdjTIOuTRpeEÅtäTrpoTIrOten`

## Solution — layered decode

Swedish wordplay → network service → GSM audio codec → Morse → Base32.

### Step 1 — decode the hints to find the port

**Hint 1:** strip every `x`, `y`, `z`:

```
x y z x y z x d y z x u y z x y p z e t x y ä z r x y z p x o y z x r t e y z x y z x y z n x y z
            →     d       j       u       p  e  t       ä  r        p  o        r  t  e         n
```

Result: `djupetärporten` → *"djupet är porten"* ("the depth is the port").

**Hint 2:** extract the uppercase letters from the mixed-case string:

```
ÅTdjTIOuTRpeEÅtäTrpoTIrOten
↓
Å T T I O T R E Å T T I O
↓ (Swedish number words)
ÅTTIOTRE (83) + ÅTTIO (80)  →  8380
```

The port is **8380**, confirmed by both hints.

### Step 2 — grab the signal

```bash
nc challs.undutmaning.se 8380 > signal.bin
```

About 167 KB of binary. Inspecting the file tail reveals a plaintext trailer:

```
... gsm 6.10\n
```

That's the format tell: **GSM 6.10** speech codec.

### Step 3 — convert GSM to WAV

Strip the trailer, then feed the raw GSM into `sox`:

```bash
# Strip the " gsm 6.10\n" trailer
python3 -c "
data = open('signal.bin','rb').read()
idx = data.rfind(b' gsm 6.10')
open('signal.gsm','wb').write(data[:idx])
"

# Convert to PCM WAV (8000 Hz, mono)
sox -t gsm -r 8000 -c 1 signal.gsm signal.wav
```

GSM 6.10 encodes 160 samples per 33-byte frame. The truncated file is 167,838 bytes = 5,086 frames exactly — the clean division is a good sanity check that the trailer strip lined up. Total audio: ~1 min 42 s.

### Step 4 — identify the signal

FFT on 1-second windows shows a single dominant tone at **~725 Hz** with clear on/off keying — **CW (Continuous Wave) Morse**, matching the submarine-cable / telegraph flavour of the story.

### Step 5 — decode the Morse

Envelope detection (20 ms RMS windows, threshold at 20 % of peak) gives run-length states. Timing cleanly separates into three bins:

| Element | Duration | Meaning |
|---------|----------|---------|
| Short ON | 80–100 ms | Dot (`.`) |
| Long ON | 300–320 ms | Dash (`-`) |
| Short OFF | 100–120 ms | Intra-character gap |
| Medium OFF | ~1380 ms | Inter-character gap |
| Long OFF | ~4020 ms | Word gap |

Dash:dot ≈ 3:1, char-gap:dot ≈ 14:1, word-gap:dot ≈ 40:1 — standard Morse ratios, slightly stretched.

Decoded message:

```
BRA JOBBAT AVKODA NU OVXGI5LUPNZGK3LPOJZWK7I
```

- *"BRA JOBBAT"* = "Good job"
- *"AVKODA NU"* = "Decode now"
- `OVXGI5LUPNZGK3LPOJZWK7I` — the payload

The encoder used the Swedish Morse extensions (`Å = .--.-`, `Ä = .-.-`, `Ö = ---.`) in the prose portion, but the payload uses only A–Z + 2–7.

### Step 6 — Base32 decode

The payload's alphabet (uppercase A–Z plus digits 2–7) is the Base32 alphabet (RFC 4648). 23 chars means 1 `=` of padding:

```bash
$ echo "OVXGI5LUPNZGK3LPOJZWK7I=" | base32 -d
undut{remorse}
```

The flag is a pun: **re-morse** = "re-Morse", the entire thing was re-encoded through Morse.

## Flag

See [flag.txt](./flag.txt)

## Tools used

- `nc` — connect to the challenge service
- `sox` (v14.7.1+) — GSM 6.10 → PCM WAV conversion
- `python3` + `numpy` — signal envelope analysis and Morse timing extraction
- `base32` — final payload decode

## Key takeaways

- **Layered CTF challenges** stack encodings: wordplay → network → codec → Morse → Base32. Each layer has its own tell (`djupet är porten`, ` gsm 6.10\n` trailer, 725 Hz tone, Base32 alphabet).
- **GSM 6.10 is identifiable by the trailing `gsm 6.10\n` string** the challenge served — no magic header, just plaintext at EOF.
- **Frame-count divisibility** (167,838 / 33 = 5086 exactly) is a good "did I strip the trailer correctly" sanity check before feeding to sox.
