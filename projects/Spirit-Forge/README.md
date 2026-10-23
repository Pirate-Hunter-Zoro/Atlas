# Spirit Forge

An original anime-inspired tactical roguelite, built to grow its creator's engineering
skills before May 2027 and for as long as it stays fun afterward.

Lead a spirit guild through shifting realms. Plan routes, combine techniques, outwit
rivals, and forge equipment. The game's systems are the algorithm exercises.

Only coaching documents and Atlas metadata exist. There is no game or installed toolchain.

- `RULES.md`: the coaching contract, loaded by Atlas.
- `QUESTS.md`: playable milestones and expansion choices.
- `TUTOR.md`: current lesson state, maintained through `board memo`.
- `AGENTS.md`: entry point for assistants outside the board.

Start a teach session on this subject: “Coach me through Spirit Forge. Read the rules
and current memory. Begin with the first unfinished quest, one step at a time.”

## Toolchain

Nothing below is installed yet. Each tool arrives as a line in this subject's `mise.toml`
or `Brewfile`, committed in the lesson that introduces it. Atlas's `scripts/setup.sh` then
installs and updates it on every Mac.

Every Mac:

- Rust via mise, with `rustfmt` and `clippy`, plus the `aarch64-unknown-linux-musl` and
  `x86_64-unknown-linux-musl` targets from Forge a static spirit.
- zig 0.17.0 and zls 0.17.0 via mise, from Realm warden.
- cargo-zigbuild 0.24.0 via mise's github backend, never brew: brew's pulls in brew zig
  and llvm.
- Flutter via mise, stable channel, which includes Dart.
- Podman (brew) from Ship a reproducible realm, plus `tools/podman-machine.sh`: `T_ROLES`
  coding, empty `T_INSTALL`, `T_MANUAL` naming `podman machine init`, a `T_CHECK` that a
  machine runs and the client and machine versions agree, a report-only `T_UPDATE`,
  `T_EVERY_DAYS` 7 and `T_STALE_DAYS` 30. The machine lives on the coding laptop only, so
  `scripts/ship.sh` runs there.
- Lean 4 via elan (setup.sh's lean branch), with a Mathlib-free Lake package at the
  subject root and its sources in `spec/`.

The first client target is Flutter web in Chrome. It needs no Xcode or Android SDK, and
widget tests run on the Dart VM.

Coding laptop only, when a device target is chosen:

- Android Studio, a cask in this subject's `Brewfile`. Its bundled JDK serves Gradle, and
  `ANDROID_HOME` is `~/Library/Android/sdk`. No `android-commandlinetools` cask: its second
  SDK would shadow Studio's.
- `tools/android-sdk.sh`, running `sdkmanager --update` with a timeout and closed stdin.
- Xcode from the App Store, with `tools/xcode.sh` only reporting. No CocoaPods.

Once only, by a person: `podman machine init` with chosen CPUs, memory and disk. When a
device target is chosen, also the Android licences, the Xcode licence and
`xcodebuild -runFirstLaunch`, the Studio wizard, AVDs, and Apple ID signing.
