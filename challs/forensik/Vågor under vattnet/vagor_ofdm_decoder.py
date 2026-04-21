#!/usr/bin/env python3

import argparse
import struct
import sys
from pathlib import Path

import numpy as np


# ─── 802.11 OFDM Constants ───────────────────────────────────────────

NFFT = 64                    # FFT size
NCP = 16                     # Cyclic prefix length
NSYM = NFFT + NCP            # Total OFDM symbol length (80 samples)
NDATA_SC = 48                # Data subcarriers per OFDM symbol
NPILOT_SC = 4                # Pilot subcarriers

# Data subcarrier indices (802.11a spec, Table 17-6)
# Subcarriers -26 to -1 and 1 to 26, excluding pilots at -21, -7, 7, 21
DATA_SC_IDX = np.array([
    i for i in range(-26, 27)
    if i != 0 and i not in (-21, -7, 7, 21)
])

PILOT_SC_IDX = np.array([-21, -7, 7, 21])

# Long Training Field (LTF) known frequency-domain values (802.11a spec, Table L-6)
# The spec defines L_{-26} to L_{+26} in subcarrier order:
_LTF_SUBCARRIERS = [
    # L_{-26} through L_{-1}
     1,  1, -1, -1,  1,  1, -1,  1, -1,  1,  1,  1,  1,  1,  1, -1,
    -1,  1,  1, -1,  1, -1,  1,  1,  1,  1,
    # L_{0} (DC — always 0)
     0,
    # L_{+1} through L_{+26}
     1, -1, -1,  1,  1, -1,  1, -1,  1, -1, -1, -1, -1, -1,  1,  1,
    -1, -1,  1, -1,  1, -1,  1,  1,  1,  1,
]
# Map to FFT bin order: subcarrier k → bin (k + 64) % 64
LTF_FREQ = np.zeros(NFFT, dtype=complex)
for i, val in enumerate(_LTF_SUBCARRIERS):
    sc = i - 26  # subcarrier index: -26 to +26
    fft_bin = (sc + NFFT) % NFFT
    LTF_FREQ[fft_bin] = val

# RATE field → (modulation, coding_rate, data_bits_per_symbol)
RATE_TABLE = {
    0b1101: ("BPSK",  0.5,  24),   # 6 Mbps
    0b1111: ("BPSK",  0.75, 36),   # 9 Mbps
    0b0101: ("QPSK",  0.5,  48),   # 12 Mbps
    0b0111: ("QPSK",  0.75, 72),   # 18 Mbps
    0b1001: ("16QAM", 0.5,  96),   # 24 Mbps
    0b1011: ("16QAM", 0.75, 144),  # 36 Mbps
    0b0001: ("64QAM", 0.667, 192), # 48 Mbps
    0b0011: ("64QAM", 0.75, 216),  # 54 Mbps
}

# Convolutional code generator polynomials (K=7)
# g0 = 133 (octal), g1 = 171 (octal)
CC_G0 = 0o133  # 0b1011011
CC_G1 = 0o171  # 0b1111001
CC_K = 7


# ─── Signal Processing Helpers ────────────────────────────────────────

def load_cfile(path: str) -> np.ndarray:
    """Load GNU Radio .cfile (interleaved float32 IQ pairs)."""
    raw = np.fromfile(path, dtype=np.float32)
    return raw[0::2] + 1j * raw[1::2]


def schmidl_cox_metric(samples: np.ndarray, lag: int = 64) -> np.ndarray:
    """Schmidl-Cox timing metric for OFDM frame detection.

    Computes |P(d)| / R(d) where:
        P(d) = sum of conj(r[d+k]) * r[d+k+L] over a window of L samples
        R(d) = sum of |r[d+k+L]|^2 over the same window

    Both the STF (repeating every 16 samples) and LTF (two identical
    64-sample halves) produce strong peaks at lag-64.
    """
    L = lag
    conj_prod = np.conj(samples[:-L]) * samples[L:]
    energy = np.abs(samples[L:]) ** 2

    cp = np.cumsum(conj_prod)
    ce = np.cumsum(energy)

    P = cp[L:] - cp[:-L]
    R = ce[L:] - ce[:-L]

    return np.abs(P) / np.maximum(R, 1e-10)


def find_frames(samples: np.ndarray, threshold: float = 0.9) -> list[int]:
    """Find LTF positions using Schmidl-Cox metric.

    The lag-64 autocorrelation produces TWO peaks per frame: one for the
    STF (which repeats every 16 samples, so lag-64 = 4 repetitions) and
    one for the LTF (two identical 64-sample halves). These appear as
    alternating short/long spacing (~3524 / ~5077 samples apart).

    We detect all peaks, then take every other one (the LTF peak in each
    pair) to get exactly one detection per frame.

    Returns sample indices pointing to the start of each LTF region.
    """
    metric = schmidl_cox_metric(samples, lag=64)

    # Find distinct peaks with minimum separation
    min_frame_dist = 480  # Minimum WiFi frame is ~480 samples
    idx = np.where(metric > threshold)[0]
    all_peaks = []
    for i in idx:
        if len(all_peaks) == 0 or i - all_peaks[-1] > min_frame_dist:
            all_peaks.append(int(i))

    if len(all_peaks) < 2:
        return all_peaks

    # Detect the alternating spacing pattern (STF peak, LTF peak pairs)
    # The LTF peak is the second in each pair
    spacings = [all_peaks[i + 1] - all_peaks[i] for i in range(len(all_peaks) - 1)]
    if len(spacings) >= 2:
        median_spacing = sorted(spacings)[len(spacings) // 2]
        # If we see alternating short/long, take every second peak
        short_count = sum(1 for s in spacings if s < median_spacing)
        long_count = sum(1 for s in spacings if s >= median_spacing)
        if abs(short_count - long_count) <= 2:
            # Alternating pattern: short gap (within frame) then long gap (between frames)
            # Take the FIRST peak of each pair — it's near the frame start (STF region)
            stf_peaks = [all_peaks[i] for i in range(0, len(all_peaks) - 1, 2)]
            return stf_peaks

    return all_peaks


def estimate_cfo(ltf_samples: np.ndarray) -> float:
    """Estimate carrier frequency offset from the LTF.

    The LTF contains two identical 64-sample symbols. Any CFO causes a
    phase rotation between them: phi = 2*pi*cfo*64/Fs.
    We estimate this phase from the cross-correlation of the two symbols.
    """
    sym1 = ltf_samples[32:96]
    sym2 = ltf_samples[96:160]
    # Phase of cross-correlation = CFO-induced rotation over 64 samples
    R = np.sum(np.conj(sym1) * sym2)
    return np.angle(R) / NFFT  # radians per sample


def correct_cfo(samples: np.ndarray, cfo_rad_per_sample: float,
                start_idx: int = 0) -> np.ndarray:
    """Apply CFO correction: multiply by exp(-j*cfo*n) for each sample."""
    n = np.arange(len(samples)) + start_idx
    return samples * np.exp(-1j * cfo_rad_per_sample * n)


def estimate_channel(ltf_samples: np.ndarray) -> np.ndarray:
    """Estimate channel response from the two LTF symbols.

    The LTF contains two identical OFDM symbols (no CP between them in the
    usual sense — the LTF has its own structure). We average both to reduce
    noise, then divide by the known LTF frequency values.

    IMPORTANT: CFO must be corrected BEFORE calling this function.
    """
    # The LTF region is 160 samples: 32-sample CP + two 64-sample symbols
    sym1 = np.fft.fft(ltf_samples[32:96])
    sym2 = np.fft.fft(ltf_samples[96:160])
    avg = (sym1 + sym2) / 2.0

    # Channel = received / known (avoid div by zero on null subcarriers)
    H = np.zeros(NFFT, dtype=complex)
    nonzero = LTF_FREQ != 0
    H[nonzero] = avg[nonzero] / LTF_FREQ[nonzero]

    return H


def demod_ofdm_symbol(symbol_samples: np.ndarray, H: np.ndarray) -> np.ndarray:
    """Demodulate one OFDM symbol: remove CP, FFT, equalize, extract data.

    IMPORTANT: CFO must be corrected in the input samples BEFORE calling this.
    """
    # Remove cyclic prefix
    payload = symbol_samples[NCP:]
    # FFT
    freq = np.fft.fft(payload)
    # Equalize (zero-forcing)
    H_safe = np.where(np.abs(H) > 1e-10, H, 1.0)
    equalized = freq / H_safe
    # Extract data subcarriers (map from [-26..26] to FFT bin indices)
    data = equalized[(DATA_SC_IDX + NFFT) % NFFT]
    return data


# ─── Modulation ───────────────────────────────────────────────────────

def demap_bpsk(symbols: np.ndarray) -> np.ndarray:
    """BPSK hard demapping: real part sign → bit.

    802.11a Table 17-8: bit 0 → -1, bit 1 → +1.
    So positive real → 1, negative real → 0.
    """
    return (np.real(symbols) > 0).astype(np.uint8)


def demap_qpsk(symbols: np.ndarray) -> np.ndarray:
    """QPSK hard demapping: 2 bits per symbol.

    802.11a Table 17-8: QPSK maps (b0,b1) with:
    I = (2*b0 - 1), Q = (2*b1 - 1) → positive = bit 1, negative = bit 0.
    """
    bits = np.zeros(len(symbols) * 2, dtype=np.uint8)
    bits[0::2] = (np.real(symbols) > 0).astype(np.uint8)
    bits[1::2] = (np.imag(symbols) > 0).astype(np.uint8)
    return bits


def demap_16qam(symbols: np.ndarray) -> np.ndarray:
    """16-QAM hard demapping: 4 bits per symbol.

    802.11a Table 17-8: 16-QAM constellation with Gray coding.
    I = K_MOD * (2*b0 - 1) * (2 - (2*b1 - 1)), same for Q with b2,b3.
    Positive I → b0=1, |I| < threshold → b1=1.
    """
    bits = np.zeros(len(symbols) * 4, dtype=np.uint8)
    norm = symbols / np.sqrt(10)
    re, im = np.real(norm), np.imag(norm)
    bits[0::4] = (re > 0).astype(np.uint8)
    bits[1::4] = (np.abs(re) < 2 / np.sqrt(10)).astype(np.uint8)
    bits[2::4] = (im > 0).astype(np.uint8)
    bits[3::4] = (np.abs(im) < 2 / np.sqrt(10)).astype(np.uint8)
    return bits


def demap_64qam(symbols: np.ndarray) -> np.ndarray:
    """64-QAM hard demapping: 6 bits per symbol.

    802.11a Table 17-8: 64-QAM with Gray coding.
    Positive I → b0=1, inner/outer thresholds for b1/b2, same for Q.
    """
    bits = np.zeros(len(symbols) * 6, dtype=np.uint8)
    norm = symbols / np.sqrt(42)
    re, im = np.real(norm), np.imag(norm)
    bits[0::6] = (re > 0).astype(np.uint8)
    bits[1::6] = (np.abs(re) < 4 / np.sqrt(42)).astype(np.uint8)
    bits[2::6] = ((np.abs(re) < 2 / np.sqrt(42)) | (np.abs(re) > 6 / np.sqrt(42))).astype(np.uint8)
    bits[3::6] = (im > 0).astype(np.uint8)
    bits[4::6] = (np.abs(im) < 4 / np.sqrt(42)).astype(np.uint8)
    bits[5::6] = ((np.abs(im) < 2 / np.sqrt(42)) | (np.abs(im) > 6 / np.sqrt(42))).astype(np.uint8)
    return bits


DEMAP = {
    "BPSK": demap_bpsk,
    "QPSK": demap_qpsk,
    "16QAM": demap_16qam,
    "64QAM": demap_64qam,
}

BITS_PER_SYMBOL = {
    "BPSK": 1,
    "QPSK": 2,
    "16QAM": 4,
    "64QAM": 6,
}


# ─── 802.11 Interleaver ──────────────────────────────────────────────

def deinterleave(bits: np.ndarray, n_cbps: int, n_bpsc: int) -> np.ndarray:
    """802.11a de-interleaver (Table 17-7 inverse).

    n_cbps = coded bits per OFDM symbol (48 * bits_per_subcarrier)
    n_bpsc = bits per subcarrier (1 for BPSK, 2 for QPSK, etc.)

    The interleaver has two permutations. We invert both.

    CRITICAL: The floor division in the second permutation is commonly
    mis-implemented. This was the bug that caused Viterbi garbage during
    the CTF. The spec says:

        j = s * floor(i/s) + (i + n_cbps - floor(16*i/n_cbps)) mod s

    where s = max(n_bpsc/2, 1). The floor(16*i/n_cbps) must use INTEGER
    floor division, not floating-point truncation.
    """
    s = max(n_bpsc // 2, 1)

    # First permutation inverse: k → i
    # Forward: i = (n_cbps/16)(k mod 16) + floor(k/16)
    # Inverse: k = 16*i - (n_cbps - 1) * (16*i // n_cbps)  ... but easier
    # to just build the forward mapping and invert it.

    # Build forward interleaver mapping
    # Step 1: k → i
    perm1 = np.zeros(n_cbps, dtype=int)
    for k in range(n_cbps):
        i = (n_cbps // 16) * (k % 16) + (k // 16)
        perm1[k] = i

    # Step 2: i → j
    perm2 = np.zeros(n_cbps, dtype=int)
    for i in range(n_cbps):
        j = s * (i // s) + (i + n_cbps - (16 * i // n_cbps)) % s
        perm2[i] = j

    # Combined forward: k → i → j
    forward = np.zeros(n_cbps, dtype=int)
    for k in range(n_cbps):
        forward[k] = perm2[perm1[k]]

    # De-interleaver: the interleaver maps coded position k to OFDM position
    # j = forward[k]. To de-interleave, we need:
    #   coded[k] = received[forward[k]]
    # i.e., out = received[forward]

    # Apply to all symbols
    out = np.empty_like(bits)
    n_symbols = len(bits) // n_cbps
    for sym in range(n_symbols):
        start = sym * n_cbps
        chunk = bits[start : start + n_cbps]
        out[start : start + n_cbps] = chunk[forward]

    # Handle remaining bits
    remaining = len(bits) % n_cbps
    if remaining:
        out[n_symbols * n_cbps :] = bits[n_symbols * n_cbps :]

    return out


# ─── Viterbi Decoder (K=7, rate 1/2) ─────────────────────────────────

def _cc_output(state: int, input_bit: int) -> tuple[int, int]:
    """Compute convolutional code output bits for a given state + input."""
    reg = (input_bit << 6) | state
    g0 = bin(reg & CC_G0).count("1") % 2
    g1 = bin(reg & CC_G1).count("1") % 2
    return g0, g1


def viterbi_decode(bits: np.ndarray) -> tuple[np.ndarray, int]:
    """Hard-decision Viterbi decoder for rate 1/2, K=7 code.

    Returns (decoded_bits, total_errors).
    """
    n_states = 1 << (CC_K - 1)  # 64 states
    n_pairs = len(bits) // 2

    # Precompute branch metrics table
    # branch_out[state][input_bit] = (next_state, g0, g1)
    branch_out = {}
    for state in range(n_states):
        for inp in range(2):
            next_state = ((state << 1) | inp) & (n_states - 1)  # shift in input
            # Actually for K=7: state is bits [6:1] of shift register,
            # input goes into bit 6. next_state is bits [6:1] after shift.
            next_state = (state >> 1) | (inp << (CC_K - 2))
            g0, g1 = _cc_output(state, inp)
            branch_out[(state, inp)] = (next_state, g0, g1)

    # Path metrics: [state] → accumulated hamming distance
    INF = float("inf")
    pm = [INF] * n_states
    pm[0] = 0  # Start in state 0

    # Traceback: [time][state] → (prev_state, input_bit)
    traceback = []

    for t in range(n_pairs):
        r0, r1 = int(bits[2 * t]), int(bits[2 * t + 1])
        new_pm = [INF] * n_states
        tb_entry = [None] * n_states

        for state in range(n_states):
            if pm[state] == INF:
                continue
            for inp in range(2):
                ns, g0, g1 = branch_out[(state, inp)]
                cost = pm[state] + (r0 ^ g0) + (r1 ^ g1)
                if cost < new_pm[ns]:
                    new_pm[ns] = cost
                    tb_entry[ns] = (state, inp)

        pm = new_pm
        traceback.append(tb_entry)

    # Find best final state
    best_state = min(range(n_states), key=lambda s: pm[s])
    total_errors = pm[best_state]

    # Traceback
    decoded = []
    state = best_state
    for t in range(len(traceback) - 1, -1, -1):
        prev_state, inp = traceback[t][state]
        decoded.append(inp)
        state = prev_state

    decoded.reverse()
    return np.array(decoded, dtype=np.uint8), int(total_errors)


# ─── Descrambler ──────────────────────────────────────────────────────

def descramble(bits: np.ndarray) -> np.ndarray:
    """802.11 descrambler (x^7 + x^4 + 1).

    The SERVICE field bits 0-6 are zero before scrambling, so the first
    7 received bits are the scrambler LFSR output. We brute-force the
    7-bit LFSR init state (1-127) and pick the one that descrambles
    the first 16 SERVICE bits to all zeros.
    """
    if len(bits) < 16:
        return bits

    def _run_lfsr(bits, seed):
        state = seed
        out = np.copy(bits)
        for i in range(len(bits)):
            feedback = ((state >> 6) ^ (state >> 3)) & 1
            out[i] ^= feedback
            state = ((state << 1) | feedback) & 0x7F
        return out

    # Try all 127 non-zero seeds, find the one that zeros SERVICE
    best_seed = 1
    best_zeros = 0
    for seed in range(1, 128):
        test = _run_lfsr(bits[:16], seed)
        n_zeros = 16 - int(np.sum(test[:16]))
        if n_zeros > best_zeros:
            best_zeros = n_zeros
            best_seed = seed
            if n_zeros == 16:
                break

    return _run_lfsr(bits, best_seed)


# ─── SIGNAL Field Decoder ─────────────────────────────────────────────

def decode_signal_field(signal_bits: np.ndarray) -> dict | None:
    """Decode the 24-bit SIGNAL field (always BPSK, rate 1/2).

    SIGNAL field format (24 bits):
        [3:0]  RATE (4 bits)
        [4]    Reserved
        [16:5] LENGTH (12 bits, in bytes)
        [17]   Parity
        [23:18] TAIL (6 zero bits)

    The SIGNAL field is always sent at 6 Mbps (BPSK, rate 1/2),
    so one OFDM symbol → 48 coded bits → 24 data bits after Viterbi.
    """
    if len(signal_bits) < 24:
        return None

    # Check parity (even parity over bits 0-16)
    parity = 0
    for i in range(17):
        parity ^= int(signal_bits[i])
    if parity != int(signal_bits[17]):
        return None  # Parity check failed

    # Check tail bits (should be 0)
    tail = signal_bits[18:24]
    if np.any(tail != 0):
        pass  # Warn but don't fail — some implementations are sloppy

    # Extract RATE (bits 0-3, LSB first)
    rate = 0
    for i in range(4):
        rate |= int(signal_bits[i]) << i

    # Extract LENGTH (bits 5-16, LSB first)
    length = 0
    for i in range(12):
        length |= int(signal_bits[5 + i]) << i

    if rate not in RATE_TABLE:
        return None

    mod, coding_rate, dbps = RATE_TABLE[rate]

    # Number of OFDM symbols needed for this frame
    n_sym = int(np.ceil((16 + 8 * length + 6) / dbps))

    return {
        "rate": rate,
        "modulation": mod,
        "coding_rate": coding_rate,
        "dbps": dbps,
        "length": length,
        "n_symbols": n_sym,
    }


# ─── Frame Decoder ────────────────────────────────────────────────────

def find_ltf_start(samples: np.ndarray, stf_peak: int) -> int:
    """Find the exact LTF start given an STF-region peak position.

    Cross-correlates the known LTF time-domain waveform with the received
    signal to find the precise T1 start, then backs up 32 samples for
    the GI2 (cyclic prefix).

    Returns the sample index of the LTF start (beginning of 32-sample GI2).
    """
    ltf_time = np.fft.ifft(LTF_FREQ)

    # Search in a window around the STF peak
    search_start = max(0, stf_peak + 100)
    search_end = min(len(samples) - 64, stf_peak + 300)
    if search_end <= search_start:
        return stf_peak + 160  # fallback

    # Cross-correlate to find T1 start
    best_pos = stf_peak + 192  # default: STF(160) + GI2(32)
    best_corr = 0
    for pos in range(search_start, search_end):
        seg = samples[pos : pos + 64]
        c = np.abs(np.vdot(seg, ltf_time))
        if c > best_corr:
            best_corr = c
            best_pos = pos

    # T1 start found; LTF start (GI2) is 32 samples earlier
    return best_pos - 32


def decode_frame(samples: np.ndarray, frame_start: int) -> bytes | None:
    """Decode a single 802.11 frame starting at the given sample index.

    frame_start is a Schmidl-Cox peak position (somewhere in the STF/LTF
    region). We refine it to find the exact LTF start, then:

    Frame structure:
        [10 short symbols (~128-160 samples)] STF — we skip this
        [CP (32) + 2×64 symbols (160 samples)] LTF — channel estimation + CFO
        [CP (16) + 64 (80 samples)] SIGNAL field
        [N × (CP + 64) (N×80 samples)] DATA
    """
    # Find exact LTF start
    ltf_start = find_ltf_start(samples, frame_start)

    # Check we have enough samples
    if ltf_start + 160 + NSYM > len(samples):
        return None

    ltf_samples = samples[ltf_start : ltf_start + 160]

    # Estimate and correct CFO for the entire frame region
    cfo = estimate_cfo(ltf_samples)

    # We need to correct CFO on a generous window from LTF onward
    # (we don't know DATA length yet, but 5000 samples covers most frames)
    frame_len = min(5000, len(samples) - ltf_start)
    corrected = correct_cfo(
        samples[ltf_start : ltf_start + frame_len],
        cfo, start_idx=0
    )

    # Re-do channel estimation on CFO-corrected LTF
    ltf_corrected = corrected[:160]
    H = estimate_channel(ltf_corrected)

    # SIGNAL field: one OFDM symbol after LTF
    sig_offset = 160
    if sig_offset + NSYM > len(corrected):
        return None

    sig_sym = corrected[sig_offset : sig_offset + NSYM]
    sig_data = demod_ofdm_symbol(sig_sym, H)
    sig_bits = demap_bpsk(sig_data)

    # De-interleave SIGNAL (BPSK: n_cbps=48, n_bpsc=1)
    sig_bits = deinterleave(sig_bits, n_cbps=48, n_bpsc=1)

    # Viterbi decode SIGNAL
    sig_decoded, sig_errors = viterbi_decode(sig_bits)

    # Parse SIGNAL field
    sig_info = decode_signal_field(sig_decoded)
    if sig_info is None:
        return None

    length = sig_info["length"]

    # Detect actual modulation from constellation: some captures (e.g. CTF
    # challenges) use BPSK for data regardless of what SIGNAL declares.
    # Check first DATA symbol amplitude to decide.
    data_offset = sig_offset + NSYM
    if data_offset + NSYM > len(corrected):
        return None
    probe = demod_ofdm_symbol(corrected[data_offset : data_offset + NSYM], H)
    max_mag = np.max(np.abs(probe))
    min_mag = np.min(np.abs(probe))

    if max_mag > 0 and (max_mag - min_mag) / max_mag < 0.1:
        # All subcarriers same magnitude → BPSK regardless of SIGNAL
        actual_mod = "BPSK"
    else:
        actual_mod = sig_info["modulation"]

    n_bpsc = BITS_PER_SYMBOL[actual_mod]
    n_cbps = NDATA_SC * n_bpsc
    dbps = n_cbps // 2  # rate 1/2 for BPSK (conservative)
    n_sym = int(np.ceil((16 + 8 * length + 6) / dbps))

    # Demodulate DATA symbols (using CFO-corrected samples)
    all_bits = []

    for i in range(n_sym):
        sym_offset = data_offset + i * NSYM
        if sym_offset + NSYM > len(corrected):
            return None

        sym = corrected[sym_offset : sym_offset + NSYM]
        data = demod_ofdm_symbol(sym, H)
        bits = DEMAP[actual_mod](data)
        all_bits.append(bits)

    coded_bits = np.concatenate(all_bits)

    # De-interleave
    coded_bits = deinterleave(coded_bits, n_cbps=n_cbps, n_bpsc=n_bpsc)

    # Viterbi decode
    decoded, errors = viterbi_decode(coded_bits)

    # Descramble
    descrambled = descramble(decoded)

    # Skip SERVICE field (16 bits) and extract MPDU
    if len(descrambled) < 16 + 8 * length:
        # Not enough bits — take what we have
        payload_bits = descrambled[16:]
    else:
        payload_bits = descrambled[16 : 16 + 8 * length]

    # Convert bits to bytes
    n_bytes = len(payload_bits) // 8
    frame_bytes = bytearray(n_bytes)
    for i in range(n_bytes):
        byte_val = 0
        for b in range(8):
            byte_val |= int(payload_bits[i * 8 + b]) << b  # LSB first
        frame_bytes[i] = byte_val

    return bytes(frame_bytes)


# ─── PCAP Writer ──────────────────────────────────────────────────────

PCAP_MAGIC = 0xA1B2C3D4
PCAP_VERSION_MAJOR = 2
PCAP_VERSION_MINOR = 4
PCAP_LINKTYPE_IEEE80211 = 105  # Raw 802.11


def write_pcap(frames: list[bytes], path: str):
    """Write decoded frames to a pcap file."""
    with open(path, "wb") as f:
        # Global header
        f.write(struct.pack(
            "<IHHiIII",
            PCAP_MAGIC,
            PCAP_VERSION_MAJOR,
            PCAP_VERSION_MINOR,
            0,       # thiszone
            0,       # sigfigs
            65535,   # snaplen
            PCAP_LINKTYPE_IEEE80211,
        ))

        # Packet records
        for i, frame in enumerate(frames):
            ts_sec = i  # Fake timestamps
            ts_usec = 0
            f.write(struct.pack(
                "<IIII",
                ts_sec,
                ts_usec,
                len(frame),  # incl_len
                len(frame),  # orig_len
            ))
            f.write(frame)


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Decode 802.11 OFDM frames from raw IQ samples (.cfile)"
    )
    parser.add_argument("input", help="Input .cfile (GNU Radio complex float32)")
    parser.add_argument("-o", "--output", default="output.pcap", help="Output pcap file")
    parser.add_argument(
        "-t", "--threshold", type=float, default=0.8,
        help="LTF detection threshold (0-1, default 0.8)"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Loading {input_path}...")
    samples = load_cfile(str(input_path))
    print(f"  {len(samples)} samples loaded")

    print("Detecting frames (LTF autocorrelation)...")
    frame_starts = find_frames(samples, threshold=args.threshold)
    print(f"  {len(frame_starts)} potential frames found")

    print("Decoding frames...")
    frames = []
    errors_total = 0
    for i, start in enumerate(frame_starts):
        frame = decode_frame(samples, start)
        if frame is not None and len(frame) > 0:
            frames.append(frame)
            if args.verbose:
                print(f"  Frame {i}: {len(frame)} bytes @ sample {start}")
        else:
            errors_total += 1
            if args.verbose:
                print(f"  Frame {i}: FAILED @ sample {start}")

    print(f"  {len(frames)} frames decoded, {errors_total} failed")

    if not frames:
        print("No frames decoded. Try lowering --threshold.", file=sys.stderr)
        sys.exit(1)

    print(f"Writing {args.output}...")
    write_pcap(frames, args.output)


if __name__ == "__main__":
    main()
