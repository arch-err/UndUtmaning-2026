# Vågor under vattnet

## Description
> *CASCADAs konstruktion är, av nöd tvunget, mestadels stål. Inte riktigt ideala förutsättningar för mobiltelefoni eller annan trådlös kommunikation.*
> *Harriet känner dock att det börjar bli dags att gripa även efter halmstrån och letar upp lite antenner och en SDR-sticka. Tro det eller ej, efter lite fipplande och trixande har hon snart lyckats hitta en signal (på 2412 MHz) och spela in den.*
> *Men vad är det hon fångat upp? Hjälp henne analysera signalen!*

**Category:** forensik
**Difficulty:** svår
**Files:** See [orig/](./orig/)

## Solution

**TL;DR** Raw IQ capture → 802.11 OFDM decode → pcap → WPA2 crack → decrypt → flag

### Steps

1. **Identify the signal:** `.cfile` = GNU Radio complex float32 IQ data. 773K samples at 2412 MHz = WiFi channel 1.

2. **Build 802.11 OFDM decoder from scratch:**
   - Detect frame boundaries via lag-64 autocorrelation (LTF detection)
   - Channel estimation from Long Training Field (LTF)
   - SIGNAL field decode: BPSK 1/2, 6 Mbps, 117 bytes → Beacon frame
   - Full decode pipeline: demodulate → de-interleave → Viterbi (rate 1/2, K=7) → descramble
   - 90 frames decoded with ZERO Viterbi errors

3. **Extract all frames to pcap:**
   - 69 Beacons (SSID: "Rockar dig!")
   - Auth + AssocReq/AssocResp (client connecting)
   - 4 EAPOL frames (full WPA2 4-way handshake)
   - 11 encrypted data frames

4. **Crack WPA2:**
   - SSID "Rockar dig!" = "Rocks you!" = **rockyou.txt**
   - `aircrack-ng capture.pcap -w rockyou.txt` → PSK: **bestfriends4eva**

5. **Decrypt traffic:**
   - `airdecap-ng -e 'Rockar dig!' -p 'bestfriends4eva' capture.pcap`
   - Flag in decrypted TCP payload to port 1337
   - `strings capture-dec.pcap | rg undut`

### Key Takeaways

- The SSID was literally telling us which wordlist to use
- Building a WiFi receiver from scratch is insane but it works
- The 802.11 interleaver formula is tricky — getting it wrong cascades through Viterbi

### Tools

- Python + numpy (OFDM demod, Viterbi decoder, FFT)
- PIL (image parsing)
- aircrack-ng (WPA2 cracking)
- airdecap-ng (traffic decryption)
- rockyou.txt

## Flag
See [flag.txt](./flag.txt)
