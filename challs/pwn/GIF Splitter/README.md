# GIF Splitter

## Description
> *CASCADA's meme-filtering GIF analysis system is exposed. The "vibe-coded" GIF library has a bug found by fuzzing. Read /flag.txt from the server.*

**Category:** pwn
**Difficulty:** medel
**Link:** [https://undutmaning-cascada-gif-splitter.chals.io](https://undutmaning-cascada-gif-splitter.chals.io)
**Files:** See [orig/](./orig/)

## Solution

Use-after-free in GIF parser's `realloc(ptr, 0)` → heap chunk reuse → overwrite FILENAMES entry with "/flag.txt" → zip includes real flag file. Inspired by CVE-2019-11932.

1. `chall.so` parses multi-frame GIFs, splits into individual frames, zips them
2. **Bug**: `parse_image_data` does `realloc(buf, sub_block_size)`. With size 0, this frees the buffer but the stale pointer persists in the reused stack struct
3. Next frame's filename `malloc(~57)` reuses the freed heap chunk (same tcache bin)
4. `parse_image_data` reallocs the stale pointer → operates on the filename's memory
5. LZW data containing `/flag.txt\0` overwrites the filename content
6. **Key insight**: `open()` uses a stack buffer copy (original name), but `FILENAMES[]` stores the heap copy (corrupted). Frame writes correctly, but zip reads `/flag.txt`
7. `zip_source_file("/flag.txt")` reads the actual flag → included in response ZIP

```python
# Craft GIF: frame 0 (alloc), frame 1 (free via size 0), frame 2 (UAF overwrite)
frames = [
    (57, b'B' * 57),                              # alloc in target tcache bin
    (0, b''),                                       # realloc(ptr,0) → free
    (57, b'/flag.txt\x00' + b'A' * 47),           # UAF → overwrite filename
]
# ~50% success rate due to heap layout variance
```

## Flag
See [flag.txt](./flag.txt)
