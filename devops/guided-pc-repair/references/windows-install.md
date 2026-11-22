# Windows 11 install from Ventoy — failure modes

## Decision points
- Old Ventoy (1.0.x) + new Win11 ISO → update Ventoy first: `sudo ./Ventoy2Disk.sh -u /dev/sdX` (keeps ISOs/files).
- `0xc000014c` / `\EFI\Microsoft\Boot\BCD` right after picking the ISO in Ventoy menu → it is the ISO's own boot loader failing, not the SSD. Select the ISO and press **Ctrl+W** (wimboot mode) — this bypassed the BCD error and reached Setup.
- Wrong boot device: Esc at power-on = ASUS boot menu; in ASUS BIOS check boot priority shows `UEFI: <usb>`; F10 save.
- Setup «A media driver your computer needs is missing» → do NOT chase IRST/VMD driver packs first. Shift+F10 → `diskpart` → `list volume` (ISO mounted as DVD-ROM = install files readable) → `list disk` (internal SSD listed = storage driver present). If the SSD is visible, the message is about the INSTALL IMAGE, not the disk.
- **Decisive image check:** `dism /get-imageinfo /imagefile:E:\sources\install.wim`. `Error: 13 The data is invalid` = corrupt install.wim → real cause of «media driver missing». A successful `copy` proves nothing (copies corrupt bytes). To split USB/Ventoy read error vs corrupt ISO: copy install.wim to W:\ and re-run get-imageinfo on the copy — same Error 13 → the ISO itself is bad; re-download the official ISO and verify its hash before writing to the stick.
- Testing another ISO on the stick needs a full reboot into Ventoy; same cmd window/history and same DISM `Version:` in the photo = he did not reboot.
- VMD: with VMD disabled in BIOS, inbox NVMe driver sees the SSD. Don't re-enable VMD on an installed system (INACCESSIBLE_BOOT_DEVICE).

## Bypass Setup: manual install (partitioning verified in field; apply/bcdboot = standard Microsoft method, needs a non-corrupt install.wim)
```
select disk 0        (the internal SSD — check size, never the USB)
clean
convert gpt
create partition efi size=300
format fs=fat32 quick
assign letter=S
create partition msr size=16
create partition primary
format fs=ntfs quick
assign letter=W
list volume          (verify: S FAT32 300 MB, W NTFS; if S RAW/too small → efi size typo, redo from clean)
exit
dir E:\sources\install.*            (E: = mounted ISO; .wim or .esd)
dism /get-imageinfo /imagefile:E:\sources\install.wim
dism /apply-image /imagefile:E:\sources\install.wim /index:N /applydir:W:\
bcdboot W:\Windows /s S: /f UEFI
```
Then reboot, remove USB; OOBE finishes. Drivers afterwards from ASUS support / MyASUS for the exact model.

## Hardware seen
ASUS Zenbook 14 UX3405MA, Core Ultra 9 185H, 953 GB NVMe.
