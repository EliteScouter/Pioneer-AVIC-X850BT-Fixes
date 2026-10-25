# Pioneer AVIC-X850BT — Bluetooth metadata fix · 1.07ES

Unofficial community firmware based on the original Pioneer EU130 1.06 update.
Restores Bluetooth song information on a tested AVIC-X850BT while the Android
phone remains set to AVRCP 1.6, with larger music text and a charcoal/red theme.

![Background artwork](assets/background-preview.png)

*Background asset only; the stereo draws its own text, buttons and icons over it.*

## What changes

- Uses the existing AVRCP 1.3 metadata path for the browsing/unknown-version
  decoder tail. Title, artist and album can display with the phone left at 1.6.
- Preserves the existing play/pause and next/previous command implementations.
- Enlarges Bluetooth Audio title, artist and album text.
- Adds a charcoal/red background with no STi logo. The background is shared
  across audio sources; other Pioneer buttons and blue graphics remain.
- Sets the numeric update version to **1.07** (`0x01070000`).
- Sets the English Information-page version popup caption to **Ver 1.07ES**.
  This identifies the community build; map and component version data are
  unchanged. Other languages retain their original popup captions.

Bluetooth browsing is sacrificed on the affected modern-phone path. This is
not an AVRCP 1.6 stack upgrade. No map update, CarPlay or Android Auto is included.

## Compatibility and test status

The Bluetooth fix and enlarged-text theme with an opaque background were
confirmed on one **AVIC-X850BT**, Samsung Galaxy S26 Ultra, Spotify, with phone
AVRCP set to 1.6. A previous private build was confirmed artifact-free.

**This exact 1.07ES release, its logo-free artwork and new popup caption have
not yet been tested on the head unit.** The release passes the offline checks
listed in [verification.json](docs/verification.json). Other head-unit models,
regions, phones and apps are not validated. Use only with the matching
AVIC-X850BT EU130 update family; do not infer compatibility from a similar name.

## Installation

1. Check the model and current **Application Version** in Service Information.
   The ordinary Information-page popup is not the updater's numeric version.
2. This package is for an installed update version **below 1.07**, such as the
   matching original 1.06. The updater requires a strictly higher number.
   It cannot install over private builds 1.09–1.13, or any version >= 1.07.
3. Copy this repository's **AVICX850** folder to the root of a blank FAT32
   microSD update card. The card must contain `AVICX850/APL` and
   `AVICX850/PLATFORM`. Avoid an extra nested repository folder on the card.
4. Follow the normal update procedure for this model with stable power, and
   allow the update and restart to finish. Do not interrupt power or remove
   the card during the update. Settings and Bluetooth pairings may reset.
5. Remove the update card when finished. Re-pair the phone if necessary.
   Leave Android's AVRCP setting at **1.6**.

After installation, check song changes, long titles, next/previous, play/pause,
volume overlays, source changes and disconnect/reconnect. Check the English
version popup for `Ver 1.07ES`. Report the exact model, region, phone, app,
installed version and steps to reproduce any problem; redact private data.

The numeric version 1.07 is a **custom release number**, not an official Pioneer
update. Stock 1.06 will not normally reinstall over it because it is lower.
This repository does not include a recovery image. Use an appropriate recovery
procedure if required; do not force a lower version through the updater.

## Repository contents

| Path | Purpose |
|---|---|
| `AVICX850/` | Ready-to-copy update-card folder |
| `tools/build.py` | Rebuild from an untouched matching original 1.06 package |
| `tools/pioneer_fw.py` | Manifest and firmware checksum verification |
| `assets/av-background.bmp` | Firmware background, 680×483, 24-bit BMP |
| `docs/verification.json` | Checks and hashes for this build |
| `docs/TECHNICAL.md` | Patch behavior and resource details |
| `SHA256SUMS.txt` | SHA-256 for every update payload file |

## Verify or rebuild

Verify the included update with Python 3.10 or later:

```powershell
python tools/pioneer_fw.py verify AVICX850
```

Rebuild on Windows using Python 3.10+ and the Windows `makecab.exe` utility.
No pip packages are required. Obtain an untouched matching original 1.06
package separately; the builder rejects an unexpected original PRG.

```powershell
python tools/build.py C:/firmware-original/AVICX850 C:/firmware-built/AVICX850 --work C:/firmware-work
```

Choose a new output directory. The script checks the original package, applies
the changes, verifies compressed-resource round trips and checksums, and writes
a verification report in the work directory.

## Uploading to GitHub

Create an empty repository, then upload this folder using Git or GitHub Desktop.
The PRG is about 50 MB and exceeds GitHub's browser file-upload limit; use Git
for the complete folder. See [GitHub's file-size documentation](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).
Keep the `AVICX850` directory structure intact.

See [NOTICE.md](NOTICE.md) for third-party ownership and attribution.
