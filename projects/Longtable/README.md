# Longtable

A shared tabletop companion that takes the physical materials out of Dungeons & Dragons:
the character sheets, the dice bag, the minis, the battle mat, the DM screen and the notes.
Each player's phone becomes a sheet, a dice tray and a map; the DM gets a live cockpit;
the table casts to a TV.

Built to grow its creator's engineering skills before May 2027 and for as long as it stays
fun afterward.

Only coaching documents and Atlas metadata exist. There is no game or installed toolchain.

- `RULES.md`: the coaching contract, loaded by Atlas.
- `QUESTS.md`: playable milestones and expansion choices.
- `TUTOR.md`: current lesson state, maintained through `board memo`.
- `AGENTS.md`: entry point for assistants outside the board.

Start a teach session on this subject: “Coach me through Longtable. Read the rules
and current memory. Begin with the first unfinished quest, one step at a time.”

## Shape

- Offline first. One device hosts the table on the local network; the others join by a code
  or a QR. No accounts and no internet are needed to play.
- iPad and iPhone first, with the DM on an iPad or laptop and players on phones. Flutter web
  in Safari is the first target; native iOS arrives when a device target is chosen.
- D&D 5e SRD 5.1 plus the owner's own homebrew. No copyrighted monsters, spells, art or
  adventures.
- Rust owns the rules and the authoritative server. Flutter owns the client. Zig owns the
  static tools and the cross toolchain. Kubernetes ships the table. Lean 4 specifies the
  rules. The board's speech narrates boxed text.

## Toolchain

Nothing below is installed yet. Each tool arrives as a line in this subject's `mise.toml`
or `Brewfile`, committed in the lesson that introduces it. Atlas's `scripts/setup.sh` then
installs and updates it on every Mac.

Every Mac:

- Rust via mise, with `rustfmt` and `clippy`, plus the `aarch64-unknown-linux-musl` and
  `x86_64-unknown-linux-musl` targets from Forge a static table.
- zig 0.17.0 and zls 0.17.0 via mise, from Warden and the content compiler.
- cargo-zigbuild 0.24.0 via mise's github backend, never brew: brew's pulls in brew zig
  and llvm.
- Flutter via mise, stable channel, which includes Dart.
- Lean 4 via elan (setup.sh's lean branch), with a Mathlib-free Lake package at the
  subject root and its sources in `spec/`.
- kubectl, helm and kustomize via mise; a local cluster from Ship the table.

The first client target is Flutter web in Safari on the iPad. It needs no Xcode or Android
SDK, and widget tests run on the Dart VM.

Coding laptop only, when a device target is chosen:

- Xcode from the App Store, with `tools/xcode.sh` only reporting. No CocoaPods. An Apple ID
  signs a development build; no App Store membership is required to run one on the owner's
  own devices.
- Android Studio, a cask in this subject's `Brewfile`, when an Android target is chosen. Its
  bundled JDK serves Gradle, and `ANDROID_HOME` is `~/Library/Android/sdk`.
- The local Kubernetes cluster: k3s in a Lima VM, or kind, with a free runtime such as
  colima. No Docker Desktop. `tools/cluster.sh` reports and `scripts/ship.sh` runs only on
  the coding laptop.

Once only, by a person: the cluster VM with chosen CPUs, memory and disk, and, when a device
target is chosen, the Xcode licence and `xcodebuild -runFirstLaunch`.
