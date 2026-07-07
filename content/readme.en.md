# 🎮 BayonettaTrainerV2 — Installation and Execution Guide

A modern trainer for **Bayonetta**, designed with a decoupled architecture featuring a **Backend (C++ DLL)** and a **Frontend (Python/PySide6 UI)** communicating via local TCP Sockets.

---

## 🛠️ How to Install (Step-by-Step)

### 1. Extract the Trainer Files
After downloading the `.zip` archive from the trainer release, extract its contents directly into the **game's root folder** (where the `Bayonetta.exe` executable is located).

The files that need to be placed in the game's root folder are:
* `dinput8.dll` (the C++ backend that intercepts and injects logic into the game)
* `trainer.ini` (general settings, hotkeys, and socket port configuration)
* `address.ini` (memory signature/AOB and pointer mappings)
* `scripts/` (folder containing all `.lua` scripts with mod functionalities)

> [!IMPORTANT]
> The DLL must be named exactly `dinput8.dll` and placed in the same folder as `Bayonetta.exe` so the game loads it automatically on startup.

---

### 2. Install MSVC++ Dependency (Required)
Since the trainer's backend was developed in C++, your Windows operating system must have the latest Microsoft Visual C++ runtime libraries installed.

* Download and install the official installer: **[Microsoft Visual C++ Redistributable 2015-2022](https://aka.ms/vs/17/release/vc_redist.x86.exe)**
* *Note:* Since Bayonetta is a 32-bit (x86) game, make sure to install the **x86** version (`vc_redist.x86.exe`), although installing the x64 version as well is recommended for general system health.

---

### 3. Run the Interface (Frontend)
The GUI allows you to toggle mods visually and check real-time logs.

Simply run the `BayonettaTrainer.exe` file provided in the package to open the interface directly.

> [!NOTE]
> Prefer building your own interface? The trainer's UI protocol is open (newline-delimited JSON over local TCP) — see the **UI Protocol / AutoUI** page.

---

## 💻 Advanced Customization & Scripting
If you want to understand what each setting in `trainer.ini` does or learn how to write your own mod scripts in Lua, check out the **[Configuration & Scripting Guide (EN)](file:///run/media/shadowy/8240450440450081/Users/Shadowy/Documents/GitHub/BayonettaTreinerV2/DOCS.en.md)**.


