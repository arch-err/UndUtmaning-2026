# Kapten Sträng

## Description
> *Med andan i halsen kommer CASCADAs hydrofonexpert Sune Sonarsson, och hack i häl på honom radiooperatören Henrik Hertz, inspringande till Harriet. Sune har upptäckt vad han tror är en ubåt som närmar sig CASCADA och Henrik fyller upphetsat i att han har lyckas snappa upp kommunikation från den misstänkta ubåten. Han har sparat dataströmmen i en pcapfil, som han inte riktigt lyckats tolka.*
> *Harriet frågar omedelbart om de tror att det är räddningen som kommer, men Sune har tydliga farhågor. Han tyckte sig känna igen ljudbilden tillhörande den ökände Kapten Sigvard "Sumpråttan" Strängs ubåt, USS Titan. Kaptenen är känd som bathypelagets förskräckelse och djupens gissel. Det är inte en räddingsexpedition!*
> *Kan du hjälpa dem att analysera inspelningen och förhoppningsvis stilla deras oro?*

**Category:** forensik
**Difficulty:** lätt
**Files:** [KaptenStrang.pcap](./orig/KaptenStrang.pcap)

## Solution

### 1. Analyze the PCAP
Single TCP conversation between `192.168.0.9:53287` and `10.2.0.2:8080`. Following the TCP stream reveals plaintext shell commands on what appears to be a submarine's file server.

### 2. Read the plaintext commands
The session shows:
```
ls **
cat FROM_HQ/PRIO_UPPDRAG_HK.txt
rar a -pqazxswedc123 exfil.rar TO_HQ FROM_HQ
md5sum exfil.rar
download exfil.rar
```

The RAR password is visible in plaintext: `qazxswedc123`

### 3. Carve the RAR from the stream
The RAR binary data (`Rar!` magic bytes) is transferred inline after the `download` command. I extracted the raw TCP stream, located the RAR magic (`526172211a07`), and carved it out.

MD5 verification: `464e63529654bb705fd60841021abce5` (matches the session)

### 4. Extract with password
```bash
unrar x -pqazxswedc123 exfil.rar
```

Contents:
- `TO_HQ/OPTI_CAM_01_OCRSCAN_000001.png` — periscope photo
- `FROM_HQ/PRIO_UPPDRAG_HK.txt` — classified ops orders

### 5. Analyze the image

The periscope photo shows a military base with a literal flag on a pole — and there's tiny, barely readable text on it. My first instinct was to try enhancing the image to read the text on the flag, which would have been a time sink. The text is intentionally low-res and hard to read — a red herring to waste your time on image enhancement.

I also tried `strings OPTI_CAM_01_OCRSCAN_000001.png | grep undut` — nothing. This is because the flag is stored in a **zTXt** (compressed text) PNG chunk. The keyword `optics_pov_frame` shows up in strings output, but the actual value is zlib-compressed, so it doesn't appear as a readable string. `strings` only finds uncompressed ASCII — compressed metadata is invisible to it.

### 6. Check metadata with exiftool
```bash
exiftool OPTI_CAM_01_OCRSCAN_000001.png
```

Custom field `Optics pov frame` contains the flag. `exiftool` knows how to decompress zTXt chunks — `strings` and `grep` don't.

## Flag
See [flag.txt](./flag.txt)
