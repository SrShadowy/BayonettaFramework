# Lua Scripting Guide (Bayonetta Trainer V2)

This document is the reference for creating and modifying Lua scripts for Bayonetta Trainer V2. The scripting system lets you interact with the game's memory safely and easily through a C++ API exported to Lua.

## Table of Contents

1. [Basic Script Structure](#1-basic-script-structure)
2. [Lean model: `on_enable`/`on_disable` hooks](#2-lean-model-on_enable--on_disable)
3. [Script Manifest (self-description)](#3-script-manifest-self-description)
4. [API Reference by topic](#4-api-reference-by-topic)
   — [State and arguments](#41-feature-state-and-ui-arguments) · [Logs, watch and errors](#42-logs-watching-and-errors) · [Memory: patching](#43-memory--byte-patching) · [read/write](#44-memory--direct-readwrite) · [pointers](#45-memory--pointer-chains) · [freeze](#46-memory--freezing) · [allocation](#47-memory--allocation-code-caves) · [Input: turbo](#48-input--turbo--autofire) · [stick spin](#49-input--analog-stick-spin) · [mouse spin](#410-input--mouse-spin) · [accepted tokens](#411-accepted-input-tokens-and-notes)
5. [Prelude helpers (`_lib.lua`)](#5-prelude-helpers-_liblua)
6. [Important Tips](#6-important-tips)

---

## 1. Basic Script Structure

Scripts live in the `scripts/` folder and must have the `.lua` extension. **The `scripts/` folder is the source of truth**: every `.lua` placed there is discovered automatically by the backend — no `.ini` registration needed. The file name (without extension) is the feature name. The `[Features]` section of `trainer.ini` only sets the initial state (on/off) and is optional.

A typical toggle script in "body" style looks like this:

```lua
local on = get_state("FeatureName") == 0
set_state("FeatureName", on and 1 or 0)

if on then
    -- Code to enable the mod (e.g. inject bytes, nop, etc.)
    log_info("Feature ON")
else
    -- Code to disable the mod (e.g. restore memory)
    log_info("Feature OFF")
end
```

## 2. Lean model: `on_enable()` / `on_disable()`

Instead of the style above (a body that re-runs and branches on `get_state`), a script can just declare two hooks: the **engine manages the feature state and calls the right hook**. A toggle mod becomes ~5 lines:

```lua
function manifest() return { label = "Infinite Jump", category = "PLAYER", control = "toggle" } end

function on_enable()  write_memory("func_InfJump", 0, { 0xEB }) end
function on_disable() restore_memory("func_InfJump") end
```

How it works:

* If the script defines `on_enable` and/or `on_disable`, the engine flips the state on each run and calls the matching hook. You do **not** call `get_state`/`set_state`.
* The **`FEATURE_NAME`** global is injected by the engine on every run with the script's name — use it instead of hardcoding the string (renaming the file no longer breaks anything).
* Backwards compatible: body-style scripts (without hooks) keep working exactly as before.

## 3. Script Manifest (self-description)

A script can expose a `manifest()` function. The backend calls it in an isolated pass during discovery and uses the result to build the UI automatically — right control, category, hotkey and input fields, without editing `.ini` or Python code.

```lua
function manifest()
    return {
        label    = "God Mode",   -- text shown in the UI
        category = "PLAYER",     -- UI grouping
        control  = "toggle",     -- toggle | value | freeze | action | turbo | spin
        hotkey   = "ALT+G",      -- optional; becomes the default shortcut ([Hotkeys] in trainer.ini overrides)
        description = "Ignores incoming damage",  -- UI tooltip
        args = {                 -- input fields rendered in the UI
            { name = "value", type = "float", min = 0, max = 9999, step = 10, default = 100 }
        }
    }
end
```

Rules and notes:

* All fields are optional. Without `manifest()`, the script shows up as a `toggle` in the `GENERAL` category with the file name as label.
* `control → widget` mapping in the UI: `toggle` → ON/OFF button, `value` → fields + SET, `freeze` → fields + FREEZE, `action` → plain button, `turbo` → fields + TURBO button, `spin` → fields + SPIN button.
* `args[].type` accepts `int`, `float`, `bool` and `string`; `min`/`max`/`step`/`default` configure the widget. Transport is **typed end to end**: the backend converts each argument according to the manifest `type` and `get_arg(name)` returns the value in the right type (int/float/bool/string). A `1.5` reaches memory without loss.

### AOB signatures inside the script (self-contained package)

The manifest can declare its own signatures in `signatures`, resolved into the `AddressRegistry` right after discovery. This makes a mod a self-sufficient unit — no need to edit the global `address.ini`.

```lua
function manifest()
    return {
        label = "My Mod",
        signatures = {
            -- short form: just the AOB pattern (same syntax as address.ini)
            func_MyFeature = "89 8F A0 00 00 00",
            -- long form: pattern + dereference offset after the match
            addr_Base = { pattern = "A1 ? ? ? ? 8B", offset = 1 }
        }
    }
end
```

Rules:

* The `pattern` syntax is identical to `address.ini` (hex bytes + `?` wildcards). `offset` is optional (default `0` = match address).
* **`address.ini` takes precedence.** If the symbol name already exists in `address.ini` (or in another loaded script), the script's signature is **ignored** and logged — preventing a third-party script from hijacking a shared symbol. Give your script's symbols unique names.
* Signatures that don't match fail soft (log only, no popup) — the mod just won't work, but the trainer won't crash.
* Combine with `alloc_memory` for packages that create their own memory (e.g. code caves) without external dependencies.
* The manifest probe runs in a restricted environment: only the `base`, `string`, `table`, `math` and `utf8` libs (no `os`, `io`, `dofile`, `loadfile`), and all memory functions are no-ops. The **entire script body** executes in this probe, so keep the top of the file free of side effects — just define `manifest()` and the mod logic.
* The manifest is cached at discovery; use the `reload` command (or restart) after editing.

---

## 4. API Reference by topic

Global functions exposed by the engine (`LuaEngine`), grouped by subject. `symbol` parameters always refer to keys defined in `address.ini` (or registered via `signatures`/`alloc_memory`).

### 4.1 Feature state and UI arguments

* `get_state(key)` — Returns the current state (integer) of a key (e.g. `1` enabled, `0` disabled).
* `set_state(key, value)` — Sets the state of a key.
* `get_arg(name)` — Gets an argument passed by the backend, **in the type declared** in the manifest (int/float/bool/string). Returns `0` for a missing argument (e.g. hotkey activation).

### 4.2 Logs, watching and errors

* `log_info(msg)` — Prints an informative message to the trainer console/log.
* `log_fail(msg)` — Prints an error message to the trainer console/log.

**Index note.** Besides topics 4.1–4.11 there is section **4.12 (Files and runtime security)** at the end of the reference.
* `watch_value(name, value)` — Publishes a live value to the UI (e.g. current HP, frozen value). Pushes a `watch_update` message to the connected client with `{feature, name, value}`, automatically tied to the running script. Accepts number, string, bool or nil (converted to text).
  *Example:* `watch_value("hp", read_int("addr_HP", 0))`
* `report_error(message, line?, details?)` — Reports a structured error to the UI (`script_error` message with `{feature, message, line, details}`) instead of just logging to file. Useful for immediate feedback while writing scripts.
  *Example:* `report_error("Null base pointer", 12, "addr_Base not resolved")`

### 4.3 Memory — byte patching

* `write_memory(symbol, offset, {byte1, byte2, ...})`
  Writes a byte array at the address resolved from `symbol` plus `offset`. Automatically backs up the original bytes the first time it is called.
  *Example:* `write_memory("func_DmgCombat", 0, { 0xEB })`

* `nop_memory(symbol, offset, count)`
  Fills `count` bytes with the `NOP` instruction (`0x90`) at the given address. Automatically backs up the original bytes.
  *Example:* `nop_memory("func_FireDemage", 0, 2)`

* `restore_memory(symbol)`
  Restores the original bytes of a `symbol` modified by `write_memory`/`nop_memory`. Restores **all** regions that symbol modified in a single call.

### 4.4 Memory — direct read/write

* `read_int(symbol, offset)` / `read_float(symbol, offset)` — Reads an integer or float from the resolved address.
* `write_int(symbol, offset, value)` / `write_float(symbol, offset, value)` — Writes an integer or float directly to memory.

### 4.5 Memory — pointer chains

* `write_on_pointer_int(symbol, {offset1, offset2, ...}, value)` — Traverses a pointer chain starting at `symbol` and writes the integer `value` at the final destination.
* `write_on_pointer_float(symbol, {offset1, offset2, ...}, value)` — Same for **float**. Accepts fractional values (e.g. `1.5`).

**Pointer chain rule (important).** Offset resolution is the **same** for `write_on_pointer_*` and `frozen_memory`, Cheat Engine style:

* `{}` (empty table) → uses the **symbol's own address**, no dereference.
* `{o1, o2, ..., on}` → resolves `[ ... [[symbol] + o1] ... + o(n-1) ] + on`. Reads the pointer at the symbol, adds each offset dereferencing at every step, and the **last** offset is only added (not dereferenced).

If any pointer in the chain is invalid, the operation aborts with a `[FAIL]` in the log — **without crashing the game**.

### 4.6 Memory — freezing

Useful for values the game updates constantly (e.g. health, mana). The trainer spawns a background thread that rewrites the bytes continuously.

* `frozen_memory(symbol, {offsets}, {byte1, byte2, ...})`
  Freezes the given bytes at the final address (same chain rule as section 4.5). With no offsets, pass `{}`. Calling it again on an already frozen symbol **updates** the frozen value.
  *Example:* `frozen_memory("addr_WitcherPower", {}, {0x00, 0x00, 0x80, 0x3F})`

* `unfrozen_memory(symbol)` — Stops freezing the memory of the given `symbol`.

### 4.7 Memory — allocation (code caves)

* `alloc_memory(symbol, size)` → address (integer)
  Allocates `size` bytes of **executable** memory (RWX, ideal for code caves) as close as possible to the game module, zeroes the block and **registers the address under `symbol`** — from then on `symbol` works like any AOB symbol (`write_memory`, `frozen_memory`, etc.). Calling again with the same `symbol` reuses the existing block. Returns `0` on failure.
  *Example:* `local cave = alloc_memory("cave_MyHook", 64)`

* `free_memory(symbol)`
  Frees a block created by `alloc_memory` and removes the `symbol` from the registry. **Not mandatory:** the engine automatically frees all allocations on shutdown/reload, but freeing manually is good practice when disabling a feature.

### 4.8 Input — turbo / autofire

Automatic button repetition — keyboard, mouse and gamepad (XInput) — supporting multi-target combos and a configurable trigger. Only **one** turbo is active at a time (the last `turbo_start` wins) and injection only happens while the game is in the foreground. The reference script, with every field exposed in the UI, is `scripts/Turbo.lua`.

* `turbo_start(config)` → `true`/`false`
  Enables the turbo. `config` is a table where **all fields are optional** — a missing/empty/`<= 0` field reuses the value from the last configuration used (that's how the hotkey re-enables the turbo without sending args):

```lua
turbo_start({
    target   = "W+SPACE+E+LMB+RMB", -- one or more targets separated by + (or ,)
    trigger  = "MOUSE4",            -- key the player HOLDS to fire (empty = first target)
    press_ms = 30,                  -- time HOLDING the buttons, ms (min 10, max 2000)
    gap_ms   = 30,                  -- time RELEASED between presses, ms (min 10, max 2000)
    mode     = "hold",              -- "hold" (repeats while holding the trigger) | "auto" (continuous until disabled)
})
```

  A positional form is also accepted: `turbo_start(targets, interval_ms, mode, trigger)` — `interval_ms` (full cycle) is split half/half into `press_ms`/`gap_ms`. In the table form, `interval_ms` also works as a shortcut when you don't need asymmetric timings.

* `turbo_stop()` — Disables the turbo and releases any pending synthetic key.

### 4.9 Input — analog stick spin

* `stick_spin_start(options)` → `true`/`false`
  Spins an analog stick in a full circle while a combo is held (requires the same XInput hook as the gamepad turbo). The trigger accepts gamepad (`PAD_*`), **keyboard and mouse**, mixed — keyboard/mouse are read via `GetAsyncKeyState` (global physical state). Empty/0 fields reuse the last config (useful for hotkeys).

```lua
stick_spin_start({
    stick     = "LS",             -- "LS" (left) | "RS" (right)
    direction = "left",           -- "left" (counterclockwise) | "right" (clockwise)
    period_ms = 400,              -- ms per full revolution (100–5000)
    trigger   = "PAD_R3+PAD_A",   -- combo held together (also: "MOUSE4", "SHIFT+RMB")
    consume   = true,             -- hides the PAD_* trigger buttons from the game while spinning
})
```

  Positional form: `stick_spin_start(stick, direction, period_ms, trigger)`.

* `stick_spin_stop()` — Stops the spin; the stick returns to physical control.

### 4.10 Input — mouse spin

* `mouse_spin_start(options)` → `true`/`false`
  Moves the **mouse** in circles (relative deltas via `SendInput`, like physically spinning the mouse on the desk) while the trigger is held. Doesn't depend on the XInput hook. The trigger accepts gamepad/keyboard/mouse; empty/0 fields reuse the last config.

```lua
mouse_spin_start({
    direction = "left",    -- "left" (counterclockwise) | "right" (clockwise)
    period_ms = 400,       -- ms per full revolution (100–5000)
    radius    = 120,       -- circle radius in pixels (10–2000)
    trigger   = "MOUSE4",  -- combo held (also: "SHIFT+RMB", "PAD_R3")
})
```

  Positional form: `mouse_spin_start(direction, period_ms, radius, trigger)`.

* `mouse_spin_stop()` — Stops the mouse spin.

### 4.11 Accepted input tokens and notes

**Accepted targets and triggers** (case-insensitive, inner spaces ignored — `"mouse 4"` = `MOUSE4`):

| Type | Tokens |
|---|---|
| Keyboard | `A`–`Z`, `0`–`9`, `F1`–`F24`, `SPACE`, `ENTER`, `TAB`, `SHIFT`, `CTRL`, `ALT`, `UP`/`DOWN`/`LEFT`/`RIGHT`, `BACKSPACE`, `DELETE`, `INSERT`, `HOME`, `END`, `PGUP`, `PGDN`, `NUM0`–`NUM9`, `PLUS`, `MINUS`, `COMMA`, `PERIOD` |
| Mouse | `LMB`, `RMB`, `MMB`, `MOUSE4`, `MOUSE5` (side buttons) |
| Gamepad (XInput) | `PAD_A`, `PAD_B`, `PAD_X`, `PAD_Y`, `PAD_LB`, `PAD_RB`, `PAD_LT`, `PAD_RT`, `PAD_UP`/`PAD_DOWN`/`PAD_LEFT`/`PAD_RIGHT`, `PAD_START`, `PAD_BACK`, `PAD_L3`, `PAD_R3` |

Notes:

* The game reads input at ~16 ms per frame; if an action doesn't register, increase `press_ms` (or `period_ms` for the spins).
* Trigger and targets are independent and can mix devices: holding `PAD_RB` while spamming keyboard keys works, as does holding `MOUSE5` while pulsing gamepad buttons. In mixed combos, keyboard and gamepad pulse in phase.
* For games that read input via DirectInput (like Bayonetta), the turbo injects keyboard and mouse into the game's state buffer using DIK scancodes, which usually works better than the traditional `SendInput` path.
* In `hold` mode, the physical trigger is detected from the game's real state whenever possible, and synthetic events generated by the turbo itself are ignored in the detection (no feedback loop).
* Gamepad targets/triggers require the game to import `XInputGetState` (the IAT hook is installed on demand). If the import doesn't exist, `turbo_start` returns `false` with a `[FAIL]` in the log — nothing hangs.
* `control = "turbo"` / `control = "spin"` in the manifest render the config fields + TURBO/SPIN button in the UI automatically.

**Example — fixed preset.** Copy into a new file (e.g. `DodgeTurbo.lua`) and it becomes its own button in the UI, with its own hotkey, no fields needed:

```lua
function manifest()
    return {
        label = "Dodge Turbo",
        category = "INPUT",
        control = "toggle",   -- a fixed preset needs no UI fields
        hotkey = "ALT+E",
        description = "Hold MOUSE5 to spam dodge (RMB) at 25/s",
    }
end

function on_enable()
    confirm_enable(turbo_start({ target = "RMB", trigger = "MOUSE5",
                                 press_ms = 20, gap_ms = 20, mode = "hold" }))
end

function on_disable()
    turbo_stop()
end
```

### 4.12 Files and runtime security

Scripts run **inside the game process with full memory access** (`write_memory` can rewrite any byte). So the security philosophy is: only install scripts from sources you trust — no sandbox protects against a script that can already rewrite the game's code.

Even so, the runtime is **hardened** at startup: only the functions no mod needs and that cause damage outside the modding scope are removed. **Unavailable**: `os.execute`, `io.popen` (shell/processes), `os.remove`, `os.rename` (delete/move files), `os.exit` (kill the game) and `package.loadlib` + `package.cpath` (load arbitrary native DLLs).

**File I/O stays available** — `io.open`, `io.read`, `io.write`, `os.time`, `os.date`, `os.getenv`, etc. — so a script can read a game file or save a config/preset file normally.

* `scripts_path(rel?)` — returns the absolute path of the trainer's `scripts/` folder, with optional `rel` appended. Use it to locate files: `io.open` resolves relative paths against the **game's** CWD (unpredictable), so `io.open(scripts_path("config/x.cfg"), "r")` is deterministic. The `scripts/config/` folder is created automatically.

For the common case, prefer the prelude helpers `read_file` / `write_file` / `config_save` / `config_load` (section 5.7), which resolve the path and handle errors without throwing.

---

## 5. Prelude helpers (`_lib.lua`)

The `scripts/_lib.lua` file is loaded once by the engine and exposes global helpers to all scripts (it is ignored by discovery and doesn't become a feature). The topics below mirror the regions of the file itself.

### 5.1 Logs

* `info(msg)` / `fail(msg)` — logs prefixed with `[FEATURE_NAME]`. Always log.
* `DEBUG` (global, default `false`) and `debug_info(msg)` — expected-behavior logs (ON/OFF, confirmations) only appear with `DEBUG = true`. Errors (`fail`) always show.

### 5.2 State / lifecycle

* `toggle(on_fn, off_fn)` — reads the state of `FEATURE_NAME`, flips it and calls the right function (body style, alternative to hooks). Returns `true` if it turned on.
* `is_enabled()` — current feature state as a boolean.
* `confirm_enable(ok, on_msg?, fail_msg?)` — the standard `on_enable()` pattern: logs the result (success via `debug_info`) and reverts the UI toggle on failure. Returns `ok`.

### 5.3 UI arguments

* `require_arg(name, default)` — reads an argument with a fallback when missing/zero.
* `arg_string(name, default?)` / `arg_int(name, default?)` — type-guarded `get_arg`; `""`/`0` when missing (for turbos/spins that means "reuse the last config").

### 5.4 Memory

* `bytes_from_int(n)` / `bytes_from_float(f)` — convert a number into a little-endian byte table (no `string.pack` boilerplate).
* `write_float_value(symbol, offsets?, value)` / `write_int_value(symbol, offsets?, value)` — pointer-chain writes; `offsets` is optional.
* `freeze_float(symbol, value)` / `freeze_int(symbol, value)` / `unfreeze(symbol)` — freezing without hand-building bytes.
* `assert_symbol(symbol)` — validates (guarded read) that a symbol resolved; reports a structured error and returns `false` if invalid.

### 5.5 Input: turbo (keyboard / mouse / gamepad)

Shortcuts over `turbo_start`; all return true/false. Default cycle: 60 ms.

* `mash(targets, ms?)` — classic turbo: holding the button repeats it. E.g. `mash("PAD_A")`.
* `turbo_combo(targets, trigger, ms?)` — holding the trigger mashes the combo. E.g. `turbo_combo("PAD_X+PAD_Y+PAD_A+PAD_B", "PAD_DOWN")`.
* `on_hold(trigger, targets, ms?)` — the same, in spoken order ("when holding X, mash Y").
* `turbo_auto(targets, ms?)` — presses by itself until `turbo_stop()`.
* `turbo_from_args()` — reads the standard UI args (`control = "turbo"`: target, trigger, press_ms, gap_ms, hold) and calls `turbo_start`. Works for keyboard, mouse and gamepad.

### 5.6 Input: spins (analog stick and mouse)

Shortcuts over `stick_spin_start`/`mouse_spin_start`; all return true/false. Defaults: left stick, 400 ms/rev, `consume=true`; mouse with 120 px radius.

* `spin_left(trigger, period_ms?, stick?)` / `spin_right(...)` — spins the analog stick while the combo is held. E.g. `spin_left("PAD_R3+PAD_A")`.
* `spin_from_args()` — reads the standard UI args (`control = "spin"`: trigger, stick, direction, period_ms, consume) and calls `stick_spin_start`.
* `mouse_spin_left(trigger, period_ms?, radius?)` / `mouse_spin_right(...)` — moves the MOUSE in circles (like spinning the mouse on the desk). E.g. `mouse_spin_left("MOUSE4")`.

### 5.7 Files and configuration

Safe helpers over `io` (return nil/false instead of throwing) that resolve paths deterministically — see section 4.12.

* `scripts_path(rel?)` — absolute path of the trainer's `scripts/` folder, with optional `rel` appended.
* `read_file(path)` / `write_file(path, text)` — read/write a file (a relative path is resolved against `scripts/`; absolute is used as-is). `read_file` returns `nil` if it can't open; `write_file` returns `true`/`false`.
* `config_save(name, tbl)` / `config_load(name)` — persists a flat table (string/number/bool) to `scripts/config/<name>.cfg` and reads it back with types converted. With no file, `config_load` returns `{}`.

---

## 6. Important Tips

- Always use `address.ini` to map game byte patterns or pointers instead of hardcoding addresses (ASLR changes base addresses on every launch).
- The backend handles memory page permissions (`VirtualProtect`) automatically.
- Call `restore_memory` or `unfrozen_memory` when disabling a feature to avoid game crashes.
- `restore_memory(symbol)` restores **all** regions that symbol modified (e.g. `write_memory` at offset 0 + `nop_memory` at offset 6 are undone in a single call).
- Invalid memory accesses are tolerated: they log a `[FAIL]` instead of crashing.
