# 📖 Configuration and Scripting Guide — Bayonetta Trainer V2

This guide is designed for players and creators who downloaded the compiled releases of the trainer and want to customize hotkeys, tweak network settings, or program new mods using Lua scripts.

---

## ⚙️ Understanding `trainer.ini`

The `trainer.ini` file sits in the same directory as the game executable and configures the startup behavior of the trainer backend. You can edit it with any text editor (like Notepad).

### 1. Section `[Network]` (Connection Settings)
The frontend UI connects to the game via local network connections.
* **`Port=27015`**: The network port the trainer's internal server will listen on. Change this only if another application on your PC is already using port 27015.
* **`AllowRemoteUI=0`**:
  * `0` (Recommended/Default): Only your local computer can connect to the trainer (secure).
  * `1`: Allows connections from other devices on the same local network (useful if you want to run the UI on another computer or a smartphone).
* **`AuthToken=`**: Sets an optional authentication password. If defined (e.g. `AuthToken=MySecretPassword`), any interface connecting to the trainer must submit this token in every JSON packet, or the commands will be ignored.

> **Tip for UI developers:** the protocol is newline-delimited JSON. Send `{"type":"help"}` to receive the full list of available commands (name, parameters and description) straight from the backend. See `UI/AutoUI/README.md` for the protocol reference.

### 2. Section `[beep]` (Sound Effects)
Configures the audio feedback played when mods are toggled on or off. (works only on windows for now)
* **`alert=1`**: Enable (`1`) or disable (`0`) sound effects.
* **`frequencyON=800`** / **`durationON=150`**: The frequency (Hz) and duration (milliseconds) of the beep played when a function is **activated**.
* **`frequencyOFF=600`** / **`durationOFF=150`**: The frequency (Hz) and duration (milliseconds) of the beep played when a function is **deactivated**.

### 3. Section `[Features]` (Initial State)
Determines the default state of mods when the game starts. **This section is optional**: scripts in the `scripts/` folder are discovered automatically — a mod not listed here simply starts disabled.
* The key name must be **exactly the same** as the filename of the Lua script in the `scripts/` directory (without the `.lua` extension).
* **`0`**: Disabled by default.
* **`1`**: Enabled by default.

```ini
[Features]
GodMode=0
InfiniteJump=0
```

### 4. Section `[Hotkeys]` (Keyboard Shortcuts)
Maps keyboard keys or combinations to toggle features on the fly.
* You can use simple keys (e.g., `F1`, `G`, `NUMPAD5`) or modifier combinations (`CTRL+F1`, `ALT+A`, `SHIFT+F`).

```ini
[Hotkeys]
GodMode=ALT+G
InfiniteJump=CTRL+F6
```

---

## 🛠️ How to Create New Scripts (Step-by-Step)

The primary advantage of Bayonetta Trainer V2 is its dynamic script loading. You do not need to recompile the C++ source code to write new mods; you can script them in **Lua**.

### Step 1: Find the Byte Pattern (AOB)
Instead of hardcoding memory addresses (which change due to ASLR every time the game starts), the trainer searches for unique byte sequences (Array of Bytes / AOB). Use whatever reverse-engineering tool you're comfortable with — **Cheat Engine** (attach to the running process), **IDA**, **Ghidra**, **x64dbg**, etc. The trainer doesn't care where the pattern came from; it only needs the bytes.
1. Find the assembly instruction responsible for the logic you want to change (e.g., the instruction that subtracts player health) — via live memory scanning (Cheat Engine) or static analysis of the game binary (IDA/Ghidra).
2. Copy the hexadecimal byte pattern of that instruction (e.g., `89 8F A0 00 00 00`).
3. If some bytes vary depending on updates or system settings, replace them with `?` (wildcards).

### Step 2: Register the Address in `address.ini`
Open `address.ini` and add your byte pattern under a unique tag name:

```ini
[func_PlayerDamage]
89 8F A0 00 00 00
```
*Tip:* You can list multiple alternative patterns line-by-line under the same tag to serve as fallbacks for different versions of the game.

### Step 3: Write the Lua Script
Inside the `scripts/` folder, create a new file named after your feature (e.g., `MyMod.lua`).

#### Example 1: Writing modified bytes (e.g., NOP or JMP)
Best for disabling game routines (like damage functions or collision checks):

```lua
-- Check the current status of the mod. If 0 (disabled), change to 1.
local on = get_state("MyMod") == 0
set_state("MyMod", on and 1 or 0)

if on then
    -- Overwrite 6 bytes of code at "func_PlayerDamage" with NOP (0x90) instructions
    nop_memory("func_PlayerDamage", 0, 6)
    log_info("MyMod activated successfully!")
else
    -- Automatically restores the original instructions
    restore_memory("func_PlayerDamage")
    log_info("MyMod deactivated!")
end
```

#### Example 2: Freezing values (e.g., Infinite Health or Witch Time)
Best for locking memory values to a constant:

```lua
local on = get_state("InfiniteHealth") == 0
set_state("InfiniteHealth", on and 1 or 0)

if on then
    -- Freeze health value. The trainer's background thread will rewrite it constantly.
    -- Parameters: (tag_name, table_of_offsets, bytes_to_write)
    -- Example: Freeze health to 9999 (0x27, 0x0F in little-endian hex)
    frozen_memory("addr_MaxHealth", {}, {0x27, 0x0F, 0x00, 0x00})
    log_info("Health frozen!")
else
    -- Stop freezing the memory address
    unfrozen_memory("addr_MaxHealth")
    log_info("Health unfrozen!")
end
```

### Step 4 (optional): Describe the Mod with `manifest()`
Just save the file in the `scripts/` folder — the trainer discovers it on its own and it shows up in the UI. To have the UI display a proper name, category, hotkey and value fields automatically, add a `manifest()` function at the top of the script:

```lua
function manifest()
    return {
        label    = "My Mod",        -- name shown in the UI
        category = "PLAYER",          -- UI group
        control  = "toggle",          -- toggle | value | freeze | action
        hotkey   = "ALT+H",           -- default shortcut ([Hotkeys] in the .ini overrides it)
        description = "What it does",
        args = {                      -- only for control = value/freeze
            { name = "value", type = "int", min = 0, max = 9999, step = 1, default = 100 }
        }
    }
end
```

See `Backend/LUA_API.en.md` for the full manifest reference.

### Step 5 (optional): `trainer.ini` Overrides
The `.ini` is no longer required to register mods — it exists to override defaults:

1. Under `[Features]`, add `MyMod=1` if you want it to start **enabled**.
2. Under `[Hotkeys]`, add `MyMod=ALT+H` to override the manifest hotkey.

Launch the game and the mod appears in the UI and responds to the configured shortcut.

---

## 📚 Lua API Reference

These are the global functions exposed by the C++ engine to Lua:

### State & Diagnostics
* `get_state("name")`: Returns the current state (`0` for disabled, `1` for enabled).
* `set_state("name", value)`: Updates the mod state (`0` or `1`).
* `log_info("message")`: Prints a status message to the logs.
* `log_fail("message")`: Prints an error message to the logs.

### Memory Manipulation
* `write_memory("tag", offset, {bytes})`: Writes a list of bytes starting at the resolved address + offset.
* `nop_memory("tag", offset, length)`: Overwrites instructions at address with NOP (`0x90`) instructions.
* `restore_memory("tag")`: Restores original bytes back to memory.
* `read_int("tag", offset)` / `read_float("tag", offset)`: Reads numeric values from memory.
* `write_int("tag", offset, value)` / `write_float("tag", offset, value)`: Writes numeric values directly to memory.
* `write_on_pointer_int("tag", {offsets}, value)` / `write_on_pointer_float("tag", {offsets}, value)`: Traverses pointer chains and writes values at the final destination.
* `frozen_memory("tag", {offsets}, {bytes})`: Constantly writes the given bytes to the resolved address.
* `unfrozen_memory("tag")`: Stops constantly writing to the memory address.

### Input (turbo and analog stick spin)
* `turbo_start({...})` / `turbo_stop()`: Automatically repeats inputs (keyboard, mouse, or XInput gamepad). See `Backend/LUA_API.en.md` for all options.
* `stick_spin_start({...})` / `stick_spin_stop()`: Spins an analog stick in a circle while a button combo is held.
* Prelude shortcuts (`_lib.lua`), recommended for simple scripts:
  * `mash("PAD_A")` — holding A repeats A (classic turbo);
  * `turbo_combo("PAD_X+PAD_Y+PAD_A+PAD_B", "PAD_DOWN")` — holding the trigger mashes the combo;
  * `turbo_auto("J", 80)` — presses by itself until `tu