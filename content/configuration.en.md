# Project Documentation and Configuration (Bayonetta Trainer V2)

This document provides an overview of how the **Bayonetta Trainer V2** backend works, explaining how to configure options, add hotkeys and manage memory signatures.

## File Structure

- `/scripts` - Lua scripts containing the individual logic for each mod (GodMode, InfiniteJump, etc.).
- `dinput8.dll` - The trainer backend, loaded automatically by the game.
- `trainer.ini` - Main configuration file (Features, Hotkeys, Settings).
- `address.ini` - Signature (AOB) and pointer mapping.

## Configuring `trainer.ini`

The `trainer.ini` file manages initial state, keyboard shortcuts and network settings.

### Section `[Network]`
Defines socket and security settings for external communication (e.g. Python, Web or Electron interfaces).
- `Port=27015` - Port used by the trainer's internal server.
- `AllowRemoteUI=0` - (Security) Whether the trainer accepts connections only from localhost (`0`) or from any device on the local network (`1`). Keep `0` if you are not using a mobile interface.
- `AuthToken=` - (Security) An authentication password (token). If set, any external interface must send this token (e.g. `{"token": "your_password"}`) in every JSON packet for the command to be accepted.

### Section `[beep]`
Audio feedback settings when a mod is toggled on or off.
- `alert=1` - Enables/disables the sound (1 = enabled).
- `frequencyON`, `durationON` - Frequency and duration of the activation beep.
- `frequencyOFF`, `durationOFF` - Frequency and duration of the deactivation beep.

> **Linux/Proton:** the beep works under Wine/Proton. The trainer detects Wine and, in that case, synthesizes the tone via `waveOut` (Windows `Beep()` produces no sound under Wine), honoring the same frequencies and durations. No extra configuration needed.

### Section `[Features]`
Sets the initial state of each mod (0 = off, 1 = on). **This section is optional**: scripts in the `scripts/` folder are discovered automatically; a mod not listed here simply starts disabled. The variable name must match the name of the `.lua` script in the `scripts/` folder (e.g. `GodMode=0` will run `GodMode.lua` when activated).

```ini
[Features]
InfiniteJump=0
GodMode=0
HitKill=0
```

### Section `[Hotkeys]`
Maps keyboard shortcuts to discovered scripts. The trainer will intercept these keys globally to toggle scripts. A shortcut defined here **overrides** the `hotkey` declared in the script's `manifest()` (see `LUA_API.en.md`).

```ini
[Hotkeys]
InfiniteJump=CTRL+F6
GodMode=ALT+G
```

## Configuring Addresses and Patterns (`address.ini`)

The `address.ini` file is essential for compatibility across different game versions. It does not use fixed addresses — it uses **Array of Bytes (AOB / Patterns)**.

Format:
```ini
[symbol_name]
XX XX ? ? XX XX XX, Y
```

- `XX` are exact bytes in hexadecimal; `?` are wildcards (bytes that change or don't matter).
- `Y` (optional) indicates an additional offset after the pattern is found, or which occurrence to use.
- Multiple lines under a key act as fallbacks or for reading chained pointers.

In Lua, the symbol is referenced by name. For example, the key `[func_DmgCombat]` in the `.ini` is used as `write_memory("func_DmgCombat", 0, {0xEB})` in the script.

## Adding a New Feature

1. **Find the byte pattern** - Use your reverse-engineering tool of choice (Cheat Engine, IDA, Ghidra...) to locate the instruction in the game.
2. **Add to `address.ini`** - Create a tag (e.g. `[func_MyFeature]`) and paste the byte pattern with wildcards where needed.
3. **Create the Lua script** - Create `MyFeature.lua` in the `scripts/` folder. Implement the logic using the API (see `LUA_API.en.md`). Done: the script is discovered automatically and shows up in the UI.
4. **(Optional) Add a `manifest()`** - Declare label, category, control type, hotkey and args in the script itself so the UI renders the right control (see `LUA_API.en.md`).
5. **(Optional) Override in `trainer.ini`** - `MyFeature=1` under `[Features]` to start enabled; `MyFeatur