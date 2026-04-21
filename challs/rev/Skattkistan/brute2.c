#include <stdio.h>
#include <string.h>
#include <openssl/sha.h>

static const unsigned char enc[] = {
    0xfa, 0xc2, 0xbf, 0x55, 0x6d, 0x37, 0x6e, 0x69,
    0xe9, 0x80, 0xfa, 0x45, 0x8a, 0xb4, 0x52, 0x4c,
    0x83, 0xc2, 0xc6, 0x7a, 0x8c, 0x61, 0x6d, 0x4b,
    0xd8, 0x37, 0x5e, 0x92, 0xa2, 0x11, 0x64, 0x34
};

int main() {
    unsigned char path[40];
    unsigned char h[32];
    /* First 6 bytes of SHA256(path) = enc XOR "undut{" */
    unsigned char prefix[6] = {0x8f, 0xac, 0xdb, 0x20, 0x19, 0x4c};

    printf("Prefix: %02x%02x%02x%02x%02x%02x\n",
           prefix[0], prefix[1], prefix[2], prefix[3], prefix[4], prefix[5]);
    fflush(stdout);

    for (int depth = 1; depth <= 39; depth++) {
        long long total = 1LL << depth;
        long long count = 0;

        for (long long i = 0; i < total; i++) {
            for (int bit = 0; bit < depth; bit++) {
                path[bit] = ((i >> (depth - 1 - bit)) & 1) ? 'v' : 'h';
            }
            SHA256(path, depth, h);
            if (h[0] == prefix[0] && h[1] == prefix[1] &&
                h[2] == prefix[2] && h[3] == prefix[3] &&
                h[4] == prefix[4] && h[5] == prefix[5]) {
                path[depth] = 0;
                unsigned char flag[33];
                for (int j = 0; j < 32; j++) flag[j] = enc[j] ^ h[j];
                flag[32] = 0;
                printf("FOUND depth %d: path=\"%s\"\n", depth, path);
                printf("SHA256="); for (int j=0;j<32;j++) printf("%02x",h[j]); printf("\n");
                printf("Flag: %s\n", flag);
                fflush(stdout);
                if (flag[0]=='u' && flag[5]=='{') return 0;
            }
            count++;
            if (count % 100000000 == 0) {
                printf("  Depth %d: %lld/%lld (%.1f%%)\n", depth, count, total, 100.0*count/total);
                fflush(stdout);
            }
        }
        printf("  Depth %d: done (%lld)\n", depth, total);
        fflush(stdout);
    }
    return 1;
}
