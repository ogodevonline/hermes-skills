---
name: guided-pc-repair
description: Use when guiding Vasily through PC/OS fixes via photos.
version: 1.0.0
author: hermes
license: MIT
metadata:
  hermes:
    tags: [windows, bios, ventoy, troubleshooting, step-by-step]
    related_skills: [systematic-debugging]
---

## When to Use
User fixes a laptop/PC by hand and sends screen photos; I direct each action.

# Guided PC repair (user does the hands, I read photos)

Class: remote, step-by-step troubleshooting of a physical machine (Windows install, boot errors, BIOS, USB media) where the user sends screen photos and runs what I say.

## Always-on rules (user preferences)
- ONE step per message. Format: 1–2 lines of what the last photo shows → `**Шаг N:**` one action (commands in one code block) → what to photograph/report back. Never dump the whole plan — the user explicitly hates «простыня».
- Keep a running list of what was ALREADY tried (from his recap or earlier turns) and never re-issue an action from it. Before each step ask: is this new information or a new action? Repeating a tried step = «водишь по кругу», he gets angry. If I made that mistake, admit it in one line and give a genuinely new step.
- Every step must either change something new or gather a decisive fact (prefer a diagnostic that splits hypotheses: e.g. `list disk` tells «disk visible → bypass setup» vs «not visible → controller/BIOS»).
- Read the photo carefully (versions, labels, sizes, footer hints like `WIMBOOT Mode`, build numbers) and correct my own earlier wrong claims explicitly when the photo contradicts them.
- Mark guesses as guesses.
- Read his typed commands in the photo before the errors (e.g. `efi size=16` typed instead of 300 → «volume too small»); point at the exact typo.

## Procedure
1. Rebuild the tried-list from history.
2. Pick the cheapest decisive diagnostic not yet done.
3. One step → wait for photo → interpret → next.
4. Before interpreting a result, check the photo's command history/versions to confirm the step was actually done (e.g. same cmd window + DISM 26100 = he did NOT reboot into the other ISO). If not, say so in one line and re-issue only that step.
5. «media driver missing» while diskpart sees the SSD → test the image: `dism /get-imageinfo` on install.wim; Error 13 «data is invalid» (also on a copy to SSD) = corrupt ISO, not drivers/Ventoy.
6. When the evidence says a GUI tool's error is false (e.g. installer says driver missing but diskpart sees the disk), stop fighting the GUI and bypass it.

## References
- `references/windows-install.md` — Windows 11 install via Ventoy: 0xc000014c, «media driver missing», VMD, manual DISM install.
