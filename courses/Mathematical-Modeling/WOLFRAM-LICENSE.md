# Wolfram licensing — record

Two separate entitlements are in play. Keep them straight; they have nothing to do with each
other.

**This file contains live licence keys.** It lives here at the owner's instruction on the
understanding that this repository is private. If the repo is ever made public, forked, or
shared with a collaborator, these are exposed — and git history keeps them after deletion.

---

## 1. What is actually running: Wolfram Engine 15.0.0

Two installs now, one entitlement. The free Engine licence attaches to a Wolfram ID, not to a
machine, so the same personal ID activates both — but **each machine has to be activated once**,
and that step is interactive.

### compute301 (Laureate) — ACTIVATED

| Field | Value |
| --- | --- |
| Product | Wolfram Engine 15.0.0 (free for developers) |
| Wolfram ID | **a personal Gmail account** — deliberately not the university address |
| Activated | 24 August 2026, on `compute301` |
| Install path | `~/WolframEngine/15.0` (7.2 GB) |
| Binaries | symlinked into `~/bin`, already on PATH |
| Licence record | `~/.WolframEngine/Licensing/mathpass` — **contains a password, do not copy it here** |
| Reported `$LicenseType` | Professional |

### The Mac — ACTIVATED

| Field | Value |
| --- | --- |
| Product | Wolfram Engine 15.0.0.0, from Homebrew: `brew install --cask wolfram-engine` |
| Install path | `/Applications/Wolfram Engine.app` |
| `wolframscript` | `/opt/homebrew/bin/wolframscript`, linked by the cask |
| Kernel | `/Applications/Wolfram Engine.app/Contents/MacOS/WolframKernel` |
| Activated | 30 August 2026, on the Mac, same personal Wolfram ID |
| Reported `$LicenseType` | Professional |
| Verified | `{2+2, $Version, $LicenseType}` → `{4, 15.0.0 for Mac OS X ARM (64-bit) (May 26, 2026), Professional}` |
| Front end | present — `UsingFrontEnd` works, so notebooks export to PDF at full fidelity |

**One thing had to be configured, and it is not obvious.** The cask links the `wolframscript`
that lives inside the bundled *Wolfram Player*, and that copy cannot find the Engine's kernel on
its own — it fails with *A WolframKernel location could not be determined*, which reads like a
broken install and is not one. Fixed once, persistently, with

```
wolframscript -configure WOLFRAMSCRIPT_KERNELPATH="/Applications/Wolfram Engine.app/Contents/MacOS/WolframKernel"
```

After that the kernel starts and says what it actually needs, which is activation.

**To activate it — this needs you, in a real terminal.** Open Terminal.app and run

```
wolframscript -activate
```

and answer with the **personal Gmail Wolfram ID** and its password — not the `@utulsa.edu` one.
Section 2 explains why that distinction matters. It must be a genuine interactive terminal:
Claude Code's `!` bash mode is not one, gives both prompts empty input, and fails instantly with
"Incorrect username or password", which looks like a typo and is not.

Done on 30 August 2026. The kernel evaluates, and — the useful surprise — a **front end is
available** on this machine in a way it was not on the headless node, so
`Export[out.pdf, Import[nb]]` produces a real Mathematica notebook printout rather than a
transcription. `scripts/nb2pdf.wls` is built on that and is now the primary route to a
submission; `scripts/nb2tex.py` remains the fallback for a machine where this activation has not
been done.

Verified working: `2+2` → 4, `$Version` → 15.0.0 for Linux x86-64, and `Export` of a `Plot`
produces a valid PNG.

**Why a personal account.** The free Engine entitlement attaches to whatever Wolfram ID claims
it and is unrelated to any university licence. A school address stops working at graduation; the
Engine authentication does not expire. Claiming it on `mtf6056@utulsa.edu` would have thrown the
licence away on graduation day for no reason.

Claimed through `wolfram.com/engine/free-license` in a **private browser window** — necessary so
it would not silently bind to the signed-in university ID.

**One open question.** The `mathpass` entry contains a field reading `20261003`, which has the
shape of an expiry date of 3 October 2026. Wolfram's licensing FAQ states the free
authentication does not expire. These disagree. If the Engine stops working in early October
2026, look here first; re-activation on the same personal ID should resolve it.

**Re-activating** (new machine, or if it lapses): run `wolframscript` from a **real terminal**
and answer the Wolfram ID and password prompts. It must be a genuine interactive terminal —
Claude Code's `!` bash mode is not one, and gives both prompts empty input, failing instantly
with "Incorrect username or password" which misleadingly looks like a typo.

---

## 2. What we gave up on: Mathematica 15.0.1 under the TU site licence

Installed successfully without root, then abandoned: **the site licence cannot be
self-activated.** Automatic web activation silently falls through to the manual prompt, and
self-service manual activation in the account portal returns "We are unable to generate a
password with the information provided." The password has to be issued by a site administrator.

The install was deleted afterwards, reclaiming 11.4 GB. Nothing here is currently installed.

| Field | Value |
| --- | --- |
| Licence | Site License, University of Tulsa |
| Wolfram ID | mtf6056@utulsa.edu |
| Valid | 15 September 2011 – **14 October 2026** |
| Product page | `account.wolfram.com/products/5ac5e6a7-55b8-4a1e-9832-3d4290835e65` |
| Site administrators | Chuck Mason, Jonathan Oxton, Dale Doty (all @utulsa.edu) |

Dale Doty is also the MATH 7013 instructor, which is why he is the addressee of the drafted
request in `wolfram-activation-email.txt`.

### Activation keys

| Key | Status |
|---|---|
| 3375-5439-AX7GVA | used elsewhere |
| 3375-5439-E4LR24 | used elsewhere |
| 3375-5439-82UVVG | used elsewhere |
| 3375-5439-S6T5J6 | available — **none consumed**, activation never succeeded |
| 3375-5439-KPKWX5 | available |

### This machine, if the request is ever pursued

| Field | Value |
| --- | --- |
| Host | compute301 |
| MathID / MachineID | 6508-30300-87941 (stable across kernel restarts) |

**A misdiagnosis worth not repeating.** This failure was initially blamed on a blocked
`activate.wolfram.com`. That hostname does not exist anywhere — public DNS returns NXDOMAIN for
it. Every real Wolfram host resolves and answers from this node. The network was never involved;
it is a licence policy restriction. Do not send anyone to IT over this.

---

## 3. Other options, if the Engine ever falls over

- **Mathematica Online** — already included in the TU entitlement, 55,000 cloud credits, no
  activation, full interactivity, saves real `.nb` files. The strongest fallback.
- **Wolfram Player** — free, runs lesson notebooks with working `Manipulate` sliders, cannot
  evaluate anything you type. A `WolframPlayer` binary also ships inside the Engine bundle.
- **Player + Engine combined into one working system** — impossible. Player's front end refuses
  to evaluate by design and cannot be pointed at another kernel; the Engine has no front end.
