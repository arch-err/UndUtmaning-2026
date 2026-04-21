# Fråga fisken

## Description
> *Harriet tycker det mesta känns jobbigt, men forskaren Rosetta Rödspätta har en idé.*
> *Hon berättar om *Piscis Cerebrum*, ett forskningsprojekt där de försöker kommunicera med olika fiskarter för att kunna förstå dem. På en filserver sparar de tolkningar av hjärnaktiviteten hos fiskarna. Kanske har någon av fiskarna en lösning på de nuvarande problemen...*
> *Rosetta har även tillgång till webinterfacets källkod, vilket kanske kan underlätta.*
> *Kan du hjälpa Harriet att leta?*
> *Filserverns webinterface kör på [https://undutmaning-fraga-fisken.chals.io](https://undutmaning-fraga-fisken.chals.io).*

**Category:** web
**Difficulty:** lätt
**Link:** [https://undutmaning-fraga-fisken.chals.io](https://undutmaning-fraga-fisken.chals.io)
**Files:** [file-server.ts](./orig/file-server.ts)

## Solution

The source code reveals a path traversal vulnerability in the `sanitize()` function:

```typescript
function sanitize(path: string) {
  return path.replaceAll(/^\.\./g, "");
}
```

This regex only strips `..` at the **start** of the string (the `^` anchor). Any `..` that appears mid-path is untouched. So a path like `x/../../etc/passwd` passes through sanitize unchanged.

To explore above BASE_DIR, use `../../..` — the sanitize strips the leading `..`, leaving `/../..` which resolves up from the base directory:
```
/list-dir?path=../../..    → finds "flaggfisk"
/read-file?path=../../../flaggfisk  → flag
```

The fish files themselves contain hints:
- **babelfisk**: "Same same but different" + "↑↑" (go up)
- **delfin**: "Ajöss och tack för fisken!" (So long and thanks for all the fish)
- **tigerhaj**: "This is my territory" (wrong direction)

## Flag
See [flag.txt](./flag.txt)
