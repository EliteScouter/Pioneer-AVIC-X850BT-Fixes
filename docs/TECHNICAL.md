# Technical notes

## Metadata

The three Communication.exe version-decoder tails in the EU130 1.06 PRG use
`SETT` plus a changed literal (`-0x2003` to `-0x2002`) so `NEGC` returns
`0x2001` for the browsing/unknown tail. Early 1.0 and 1.3 branches remain stock.

| PRG byte offset | Original | Patched |
|---|---|---|
| 0x195CBFC | 20 88 | 18 00 |
| 0x195CCF6 | FD DF | FE DF |
| 0x195F0B6 | 20 88 | 18 00 |
| 0x195F1B6 | FD DF | FE DF |
| 0x1961FE8 | 20 88 | 18 00 |
| 0x1961FFE | FD DF | FE DF |

The tested phone remains configured for AVRCP 1.6; the head unit selects its
existing metadata path. Phone logs from private testing showed track-change
notifications and GetElementAttributes requests, with no SetBrowsedPlayer.
Private phone reports are intentionally not bundled.

## Text and theme

`layoutCreators.dat` changes only Bluetooth main-screen text instances:
title 28×32 -> 32×36 (height 40, y108), artist 22×26 -> 28×32 (height 36),
album 22×26 -> 24×28 (height 32). The 32×36 font name is appended to its ASCII
pool, shifting the UTF-16 pool by 16 bytes. Button rectangles are unchanged.

The shared AV image is `av/P24_bmp/P24_AV_0001.bmp`, 680×483, 24-bit.
Only its pixels in `image.iarc` change; the original header, archive offsets,
entry lengths and trailing alignment bytes are retained.

GraphicsLib's BMP loader reduces RGB to RGB555 and can use black as a
transparent key. The public background uses a minimum value of 8 in every
channel, with the stock R/B multiples-of 8 and G multiples-of 4 precision.
It has zero pixels that reduce to transparent black. The same palette floor
eliminated stale-screen fragments in the user-confirmed private 1.12 build.

## Version popup

The photographed popup on Information reads `Version 1.000000`. Its English
caption format is `Version %s` in `initDB.dat`, at decoded byte offset
0x1D0140. The public build replaces the UTF-16 caption with `Ver 1.07ES`,
exactly the same byte length including its terminator. The formatter receives
its original argument, which the new literal caption does not consume.
No runtime component version, map version, updater comparison, or executable
instruction is changed for this display label. Other localized captions remain
stock. The modified popup requires a hardware check.

The actual numeric update version is 0x01070000 in the PRG and both VER files,
including the PRG-header copy embedded in the platform manifest.

## Compression and validation

Both modified DAT resources remain in their original ROM slots. Changed CE
pages are encoded with makecab LZX, wrapped in CE page headers, decoded and
compared with the desired resource. Selected unchanged pages may be losslessly
recompressed to recover space. Neighboring resources are not relocated.

The builder checks manifest CRCs, PRG payload/header sums, exact resource
round trips, the six metadata windows, permitted PRG change ranges, palette
precision, and the list of changed package files. Offline checks do not certify
hardware behavior on every device or eliminate firmware-update risk.

## Numbering

Public 1.07ES is based on original 1.06 and deliberately uses a lower number than
private development builds 1.09–1.13. Those private units cannot install 1.07 by
the ordinary updater. No downgrade bypass is included.
