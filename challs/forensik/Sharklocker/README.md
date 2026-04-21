# Sharklocker

## Description
> *Konrad Kelpskog är fortfarande försvunnen, men Harriet har hittat vad som verkar vara hans laptop i ett av omklädningsrummen.*
> *Tillsammans med laptopen fanns ett sönderrivet papper, en halvtom flaska Ramlösa med citrussmak, två AA-batterier ihopsatta med en gummisnodd samt en tub blixtlim av märket UHU Sekundenkleber. Kan det finnas någon information av värde på laptopen? Någon ledtråd till var Kondrad tagit vägen? Någon lösning på röran CASCADA hamnat i?*
> *Lyckligtvis verkar Konrad inte ha ansett sig behöva lösenordsskydda laptopen så Harriet kan enkelt göra en kopia på C-driven, men delar av informationen på den är inte tillgänglig. Harriet tittar lite närmare på det sönderrivna pappret i hopp om att få några uppslag. Konrad, som vanligt glömsk och paranoid, verkar ha skyddat sin information bakom ett pussel han bara tror sig kunna lägga själv...*
> *Harriet ger dig tillgång till kopian hon tog på C-driven. Kan du hjälpa Harriet att komma åt informationen på Konrads laptop?*

**Category:** forensik
**Difficulty:** lätt
**Files:** [C-drive.zip](./orig/C-drive.zip)

## Solution

BitLocker-encrypted VHD with recovery key split across 8 hidden parts in various steganographic/forensic locations.

**Recovery key:** `674806-092587-219769-308396-244310-199694-411587-406120`

### How each part was found

**Part 1 (674806):** Torn paper image — visible digits on the scanned image.
> Visual inspection — the digits are readable on the torn paper scan

**Part 2 (092587):** Hajmat.docx metadata — hidden in the `dc:title` field.
```bash
# .docx is a zip — extract and query the XML metadata
unzip -p Users/user/Documents/Hajmat.docx docProps/core.xml | xq -x '//dc:title'
```

**Part 3 (219769):** Chrome browser history — a suspicious search stands out.
```bash
# Dump Chrome browser history and look for anything unusual
sqlite3 "C/Users/user/AppData/Local/Google/Chrome/User Data/Default/History" \
  "SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC;" | rg "\d{6}[^\d]"
# One entry is a Google search for a bare 6-digit number — that's our part
```

**Part 4 (308396):** 7z archive in Downloads — password-protected.
```bash
# Found a rockyou subset in Downloads alongside the archive — hint to bruteforce
7z2john C/Users/user/Downloads/part4.7z > hash.txt
john --wordlist=C/Users/user/Downloads/rockyou-65.txt hash.txt
# Password: nokia5200
7z x C/Users/user/Downloads/part4.7z -pnokia5200
cat part4.txt
```

**Part 5 (244310):** MP3 file with suspicious name — `P[A]rt$_Warmup^.mp3`. Playing it forward sounds like noise.
```bash
# Reverse the audio and listen
ffmpeg -i "Users/user/Music/P[A]rt\$_Warmup^.mp3" -af areverse reversed.mp3
# Spoken digits: "two four four three one zero" → 244310
```

**Part 6 (199694):** PDF document — contains the digits as rendered text.
```bash
# Extract text from the PDF
pdftotext C/Users/user/Documents/Part6.pdf -
```

**Part 7 (411587):** JPEG with a hidden thumbnail — the EXIF thumbnail contains a different image than the main photo.
```bash
# Extract the embedded EXIF thumbnail
exiftool -b -ThumbnailImage C/Users/user/Pictures/part-7.jpg > thumbnail.jpg
# The thumbnail shows the digits — invisible in the full-size image
```

**Part 8 (406120):** Emoji document — digits encoded using an emoji substitution cipher.
> Map each unique emoji to a digit based on its position/pattern
> Decodes to: 406120


### Decryption
```bash
# The VHD on the Desktop is BitLocker-encrypted — need to expose the partition first
sudo losetup -o 65536 /dev/loop0 C/Users/user/Desktop/SharkSecret.vhd

# Decrypt with dislocker using the reconstructed recovery key
sudo mkdir -p /mnt/dislocker /mnt/bitlocker
sudo dislocker -V /dev/loop0 -p674806-092587-219769-308396-244310-199694-411587-406120 -- /mnt/dislocker
sudo mount -o loop /mnt/dislocker/dislocker-file /mnt/bitlocker

# Flag is in the decrypted filesystem
cat /mnt/bitlocker/flag.txt
```

## Flag
See [flag.txt](./flag.txt)
