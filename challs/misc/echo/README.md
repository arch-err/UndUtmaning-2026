# echo

## Description
> *Den här utmaningen kör inte på CTFd-plattformen. Instruktioner för hur du ansluter till utmaningstjänster hittar du på [informationssidan](info#anslutning-sni).*

**Category:** misc
**Difficulty:** medel

## Solution
*Unsolved — post-CTF analysis in progress*

### Static Analysis Notes
- ELF 64-bit, statically linked, stripped, 18K — compiled with GCC 13.3.0 on Ubuntu 24.04
- Takes exactly 1 argument (argc == 2), max 255 chars — probably a hostname/IP
- Uses `socket(42, SOCK_DGRAM, 0)` — protocol family 42 is unusual (not standard AF_*)
- Has `sendto` in strings — sends data over the socket
- Syscalls found: socket (41), fcntl (72), epoll_create1 (218), mmap (9)
- Receives response with recvfrom equivalent, buffer size 0xff (255)
- Name "echo" + socket + sendto = likely ICMP echo / ping variant
### Reversed Protocol

**Full binary flow:**
1. Takes exactly 1 argument (string, max 255 chars)
2. Creates `socket(AF_QIPCRTR=42, SOCK_DGRAM, 0)`
3. Builds `sockaddr_qrtr`: family=42, **node=1, port=666**
4. `sendto()` — sends argv[1] as raw bytes to node 1, port 666
5. `recvfrom()` — receives response, max 255 bytes
6. Null-terminates and `puts()` the response to stdout
7. Closes socket, exits

**It's literally an echo client.** Send a string, print whatever comes back.

**Key details:**
- AF_QIPCRTR (42) = Qualcomm IPC Router — local IPC, not network
- Destination: node=1, port=666 (0x29a) — intentionally devilish
- Error strings in rodata: "socket", "sendto", "/dev/null"
- The challenge server likely had a QIPCRTR listener on node 1 port 666
- The flag probably came back as the response (or required specific input)

**Open questions:**
- What input triggers the flag response? (could be anything, empty string, specific command)
- Was the server a real QIPCRTR service or was it tunneled/proxied?
- The SNI connection instruction in the description suggests network access was involved — maybe a remote host exposed QIPCRTR over a tunnel?
- Could we solve this post-CTF by writing our own QIPCRTR listener that the binary connects to?
