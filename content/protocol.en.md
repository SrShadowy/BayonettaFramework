# Auto Trainer UI (manifest-driven)

Standalone Python UI (tkinter, no external dependencies) that builds the interface **by itself** from the script manifests. No mod is hardcoded here: dropping a `.lua` into the backend's `scripts/` folder makes a new control appear on screen.

## Usage

```
python auto_trainer_ui.py [--host 127.0.0.1] [--port 27015] [--token PASSWORD]
```

Requires Python 3.8+ with tkinter (bundled on Windows; on Linux, install the `tk` package).

## How the interface is built

1. On connect, it sends `{"type":"hello"}` (receives `welcome` + a `state` snapshot) and `{"type":"describe"}`.
2. The `{"type":"manifest","scripts":[...]}` response carries one object per script:

| Field | Description |
|---|---|
| `name` | feature name (= `.lua` filename) |
| `has_manifest` | whether the script defined `manifest()` |
| `label` | display text (fallback: `name`) |
| `category` | UI group (fallback: `GENERAL`) |
| `control` | `toggle` \| `value` \| `freeze` \| `turbo` \| `spin` \| `action` (fallback: `toggle`) |
| `hotkey` | default shortcut, if declared |
| `description` | tooltip |
| `args[]` | `{name, type, min?, max?, step?, default?}` — defines the input fields |

3. `control → widget` mapping:

| `control` | Widget |
|---|---|
| `toggle` | ON/OFF button |
| `value` | fields + SET button |
| `freeze` | fields + FREEZE button (with active state) |
| `turbo` | config fields + TURBO button (with active state) |
| `spin` | config fields + SPIN button (with active state) |
| `action` | RUN button |

`args[].type`: `int`/`float` → spinbox, `bool` → checkbox, `string` → text field. If `value`/`freeze` comes without `args`, the UI assumes a single int `value` arg (compatibility with older backends).

## Protocol messages (TCP, newline-delimited JSON)

Sent by the UI:

```json
{"type":"hello"}
{"type":"describe"}
{"type":"help"}
{"type":"command","feature":"GodMode"}
{"type":"command","feature":"SetHoly","args":{"value":100000}}
{"type":"state","feature":"GodMode"}
{"type":"check"}
{"type":"reload"}
```

`{"type":"help"}` responds with `{"type":"help","commands":[{name,params,description}...]}` — the full list of protocol commands, handy for exploring the backend with plain `nc`/`telnet`.

If `AuthToken` is set in `trainer.ini`, every message must include `"token":"..."`.

Received from the backend:

| Message | Handling in AutoUI |
|---|---|
| `welcome` | logs game + protocol version |
| `manifest` | (re)builds the controls |
| `state` | snapshot with states + manifests; syncs the buttons |