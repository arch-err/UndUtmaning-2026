# Åtkomst nekad

## Description
> *SSH server at challs.undutmaning.se:2222. Find credentials from medical report + Roundcube email backup.*

**Category:** misc
**Difficulty:** medel

## Solution

Medical report OSINT → bcrypt crack → SSH → internal phpMyAdmin 4.8.1 LFI (CVE-2018-12613) → flag.

1. **Medical report** reveals Pelle Patchberg is a Pokémon obsessive sysadmin who:
   - Uses "Vaporeon" as username everywhere (his favorite Pokémon)
   - Reuses passwords following pattern: PokémonName+Year (e.g., Pikachu1996)
2. **Roundcube SQL backup** contains `pelle.patchberg` with bcrypt hash
3. **Cracked hash**: `Bulbasaur1997` (bcrypt, ~150 attempts with Pokémon+year wordlist)
4. **SSH access**: `vaporeon:Bulbasaur1997` on port 2222
5. **Internal network**: service check script reveals Apache + phpMyAdmin 4.8.1 + MariaDB
6. **CVE-2018-12613**: phpMyAdmin 4.8.1 LFI via `index.php?target=db_sql.php%253f/../../../../path`
7. **Info page** at `/info.php` hints flag at `/var/backups/cascada/secret.txt`
8. **LFI read**: `target=db_sql.php%253f/../../../../var/backups/cascada/secret.txt`

## Flag
See [flag.txt](./flag.txt)
