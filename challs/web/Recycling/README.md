# Recycling

## Description
> *En av CASCADAs små miniubåtar har i brist på kommunikation med hemmabasen förirrat sig iväg på egen hand ut på djupare vatten. Forskarna är oroliga för sin lilla ögonsten. Ubåten har samlat in viktiga mätvärden i veckor och var dessutom löjligt dyr!*
> *Genom ett nödsystem har man till sist lyckats etablera kontakt med ubåten över ett provisoriskt nätverk, så nu kan forskarna åtminstone komma åt ubåtens statusinterface. Tyvärr har man stött på ett problem. Ingen minns lösenordet!*
> *En av anläggningens systemadministratörer har lyckats gräva fram lite gammal trafikdata och kanske finns det något där man kan använda för att återställa accessen till systemet.*
> *Kan du hjälpa CASCADAs forskare att stilla sin oro?*
> *Du kan surfa in till ubåtens statusinterface på [https://undutmaning-recycling.chals.io](https://undutmaning-recycling.chals.io).*

**Category:** web
**Difficulty:** lätt
**Link:** [https://undutmaning-recycling.chals.io](https://undutmaning-recycling.chals.io)
**Files:** [dump.pcap](./orig/dump.pcap)

## Solution

The pcap contains mostly TLS traffic, but there's plaintext HTTP traffic to `x32.cascada.ex:8008` — an internal submarine status interface.

1. Open the pcap in Wireshark and filter for HTTP traffic
2. The first request to `x32.cascada.ex:8008/` returns an unauthenticated page
3. A subsequent request includes a cookie: `SECRET=token_wY0aHRM6gqVjEZF1yC92nKxL`
4. With this cookie, the user accesses `/` and `/stats` — authenticated pages

The "recycled" credential is the cookie from the old traffic data. Set it on the live challenge site to gain access.

```
Cookie: SECRET=token_wY0aHRM6gqVjEZF1yC92nKxL
```

## Flag
See [flag.txt](./flag.txt)
