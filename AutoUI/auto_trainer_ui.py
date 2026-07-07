#!/usr/bin/env python3
"""
Auto Trainer UI — standalone, zero dependencias (tkinter/stdlib).

A interface NAO tem nenhum cheat hardcoded: ela conecta no backend,
manda {"type":"describe"} e monta os controles sozinha a partir dos
manifestos (Etapa 3 do roadmap).

Mapeamento control -> widget:
    toggle -> botao ON/OFF
    value  -> spinbox(es) + botao SET
    freeze -> spinbox(es) + botao FREEZE (on/off)
    turbo  -> campos de config + botao TURBO
    action -> botao simples

Os args do manifesto (type/min/max/step/default) definem cada spinbox.

Uso:  python auto_trainer_ui.py [--host 127.0.0.1] [--port 27015] [--token X]
"""

import argparse
import json
import queue
import socket
import threading
import tkinter as tk
from tkinter import ttk

# ---------------------------------------------------------------- networking

class TrainerClient:
    """Cliente TCP: JSON delimitado por newline, thread de leitura propria."""

    def __init__(self, event_queue: queue.Queue):
        self.events = event_queue
        self.sock = None
        self.token = ""
        self._lock = threading.Lock()
        self._reader = None

    @property
    def connected(self):
        return self.sock is not None

    def connect(self, host: str, port: int, token: str):
        self.disconnect()
        try:
            s = socket.create_connection((host, port), timeout=5)
            s.settimeout(None)
        except OSError as exc:
            self.events.put(("log", f"Falha ao conectar: {exc}", "err"))
            return False
        self.sock = s
        self.token = token
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()
        self.events.put(("connected", None, None))
        self.send({"type": "hello"})
        self.send({"type": "describe"})
        return True

    def disconnect(self):
        with self._lock:
            if self.sock:
                try:
                    self.sock.close()
                except OSError:
                    pass
                self.sock = None

    def send(self, data: dict):
        if not self.sock:
            self.events.put(("log", "Nao conectado.", "err"))
            return
        if self.token:
            data = {**data, "token": self.token}
        try:
            with self._lock:
                self.sock.sendall((json.dumps(data) + "\n").encode("utf-8"))
            shown = {**data}
            if "token" in shown:
                shown["token"] = "******"
            self.events.put(("log", "-> " + json.dumps(shown), "out"))
        except OSError as exc:
            self.events.put(("log", f"Erro de envio: {exc}", "err"))
            self.disconnect()
            self.events.put(("disconnected", None, None))

    def _read_loop(self):
        buffer = ""
        sock = self.sock
        while True:
            try:
                chunk = sock.recv(4096)
            except OSError:
                break
            if not chunk:
                break
            buffer += chunk.decode("utf-8", errors="replace")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    self.events.put(("log", "JSON invalido: " + line[:120], "err"))
                    continue
                self.events.put(("message", msg, None))
        if self.sock is sock:
            self.sock = None
            self.events.put(("disconnected", None, None))


# ------------------------------------------------------------------- widgets

class FeatureRow:
    """Uma linha de controle gerada a partir de um manifesto."""

    def __init__(self, parent, script: dict, send_command):
        self.name = script["name"]
        self.control = script.get("control", "toggle")
        self.send_command = send_command
        self.state = 0
        self.arg_vars = {}   # name -> (tk variable, arg spec)

        self.frame = ttk.Frame(parent)
        self.frame.pack(fill="x", padx=6, pady=2)

        label = script.get("label") or self.name
        lbl = ttk.Label(self.frame, text=label, width=22, anchor="w")
        lbl.pack(side="left")

        tooltip = script.get("description", "")
        hotkey = script.get("hotkey", "")
        if hotkey:
            ttk.Label(self.frame, text=f"[{hotkey}]", foreground="#888").pack(side="right", padx=4)
        if tooltip:
            _bind_tooltip(lbl, tooltip)

        args = script.get("args") or []
        # [fallback] value/freeze precisam de input mesmo se o backend nao
        # mandou args (backend antigo ou manifesto sem args): assume um
        # arg padrao "value" int — igual ao contrato atual do get_arg().
        if not args and self.control in ("value", "freeze"):
            args = [{"name": "value", "type": "int", "default": 0}]
        self._build_args(args)

        if self.control == "toggle":
            self.button = tk.Button(self.frame, text="OFF", width=8, relief="raised",
                                    command=self._on_toggle)
            self.button.pack(side="left", padx=4)
        elif self.control == "value":
            self.button = tk.Button(self.frame, text="SET", width=8,
                                    command=self._on_send_args)
            self.button.pack(side="left", padx=4)
        elif self.control == "freeze":
            self.button = tk.Button(self.frame, text="FREEZE", width=8, relief="raised",
                                    command=self._on_send_args)
            self.button.pack(side="left", padx=4)
        elif self.control == "turbo":
            self.button = tk.Button(self.frame, text="TURBO", width=8, relief="raised",
                                    command=self._on_send_args)
            self.button.pack(side="left", padx=4)
        elif self.control == "spin":
            self.button = tk.Button(self.frame, text="SPIN", width=8, relief="raised",
                                    command=self._on_send_args)
            self.button.pack(side="left", padx=4)
        else:  # action
            self.button = tk.Button(self.frame, text="RUN", width=8,
                                    command=lambda: self.send_command(self.name, {}))
            self.button.pack(side="left", padx=4)

        # [portabilidade] cores default do tema (no Windows seria "SystemButtonFace",
        # que nao existe no Linux) — captura o que o Tk realmente usou.
        self._default_bg = self.button.cget("bg")
        self._default_fg = self.button.cget("fg")

    def _build_args(self, args):
        for arg in args:
            arg_type = arg.get("type", "int")
            name = arg.get("name", "value")
            default = arg.get("default", 0)
            if arg_type == "bool":
                var = tk.BooleanVar(value=bool(default))
                ttk.Checkbutton(self.frame, text=name, variable=var).pack(side="left", padx=2)
            elif arg_type == "string":
                var = tk.StringVar(value=str(default) if default else "")
                ttk.Entry(self.frame, textvariable=var, width=12).pack(side="left", padx=2)
            else:
                var = tk.StringVar(value=str(default))
                spin = tk.Spinbox(
                    self.frame, textvariable=var, width=8,
                    from_=arg.get("min", -10**9), to=arg.get("max", 10**9),
                    increment=arg.get("step", 1),
                )
                spin.pack(side="left", padx=2)
            self.arg_vars[name] = (var, arg)

    def _collect_args(self):
        out = {}
        for name, (var, spec) in self.arg_vars.items():
            arg_type = spec.get("type", "int")
            if arg_type == "bool":
                out[name] = bool(var.get())
            elif arg_type == "string":
                out[name] = var.get()
            elif arg_type == "float":
                try:
                    out[name] = float(var.get())
                except ValueError:
                    out[name] = float(spec.get("default", 0))
            else:
                try:
                    out[name] = int(float(var.get()))
                except ValueError:
                    out[name] = int(spec.get("default", 0))
        return out

    def _on_toggle(self):
        self.send_command(self.name, {})

    def _on_send_args(self):
        self.send_command(self.name, self._collect_args())

    def set_state(self, state: int):
        self.state = state
        on = state != 0
        if self.control == "toggle":
            self.button.config(text="ON" if on else "OFF",
                               bg="#2e7d32" if on else self._default_bg,
                               fg="white" if on else self._default_fg)
        elif self.control == "freeze":
            self.button.config(text="FROZEN" if on else "FREEZE",
                               bg="#1565c0" if on else self._default_bg,
                               fg="white" if on else self._default_fg)
        elif self.control == "turbo":
            self.button.config(text="TURBO ON" if on else "TURBO",
                               bg="#b8860b" if on else self._default_bg,
                               fg="white" if on else self._default_fg)
        elif self.control == "spin":
            self.button.config(text="SPIN ON" if on else "SPIN",
                               bg="#6a1b9a" if on else self._default_bg,
                               fg="white" if on else self._default_fg)


def _bind_tooltip(widget, text):
    tip = {"win": None}

    def show(_event):
        if tip["win"]:
            return
        win = tk.Toplevel(widget)
        win.wm_overrideredirect(True)
        win.wm_geometry(f"+{widget.winfo_rootx()}+{widget.winfo_rooty() + 22}")
        tk.Label(win, text=text, background="#ffffe0", relief="solid",
                 borderwidth=1, padx=4, pady=2).pack()
        tip["win"] = win

    def hide(_event):
        if tip["win"]:
            tip["win"].destroy()
            tip["win"] = None

    widget.bind("<Enter>", show)
    widget.bind("<Leave>", hide)


# ----------------------------------------------------------------------- app

class AutoTrainerApp:
    def __init__(self, root: tk.Tk, host: str, port: int, token: str):
        self.root = root
        root.title("Auto Trainer UI (manifest-driven)")
        root.geometry("640x600")

        self.events = queue.Queue()
        self.client = TrainerClient(self.events)
        self.rows = {}  # feature name -> FeatureRow

        # --- barra de conexao ---
        bar = ttk.Frame(root)
        bar.pack(fill="x", padx=6, pady=4)
        self.host_var = tk.StringVar(value=host)
        self.port_var = tk.StringVar(value=str(port))
        self.token_var = tk.StringVar(value=token)
        ttk.Label(bar, text="Host").pack(side="left")
        ttk.Entry(bar, textvariable=self.host_var, width=12).pack(side="left", padx=2)
        ttk.Label(bar, text="Port").pack(side="left")
        ttk.Entry(bar, textvariable=self.port_var, width=6).pack(side="left", padx=2)
        ttk.Label(bar, text="Token").pack(side="left")
        ttk.Entry(bar, textvariable=self.token_var, width=10, show="*").pack(side="left", padx=2)
        self.connect_btn = ttk.Button(bar, text="Connect", command=self._on_connect)
        self.connect_btn.pack(side="left", padx=4)
        ttk.Button(bar, text="Reload scripts", command=self._on_reload).pack(side="left", padx=2)
        self.status = ttk.Label(bar, text="desconectado", foreground="#b00")
        self.status.pack(side="right")

        # --- area de features (scroll) ---
        container = ttk.Frame(root)
        container.pack(fill="both", expand=True, padx=6)
        self.canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.features_frame = ttk.Frame(self.canvas)
        self.features_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.features_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- console ---
        self.log = tk.Text(root, height=8, state="disabled", font=("Consolas", 9))
        self.log.pack(fill="x", padx=6, pady=4)
        for tag, color in (("out", "#1565c0"), ("in", "#2e7d32"), ("err", "#b00020")):
            self.log.tag_configure(tag, foreground=color)

        root.after(100, self._poll_events)

    # -------------------------------------------------------------- conexao

    def _on_connect(self):
        if self.client.connected:
            self.client.disconnect()
            return
        try:
            port = int(self.port_var.get())
        except ValueError:
            self._log_line("Porta invalida.", "err")
            return
        threading.Thread(
            target=self.client.connect,
            args=(self.host_var.get().strip(), port, self.token_var.get().strip()),
            daemon=True).start()

    def _on_reload(self):
        self.client.send({"type": "reload"})
        self.client.send({"type": "describe"})

    def _send_command(self, feature: str, args: dict):
        msg = {"type": "command", "feature": feature}
        if args:
            msg["args"] = args
        self.client.send(msg)

    # ---------------------------------------------------------------- render

    def _rebuild_ui(self, scripts: list):
        for child in self.features_frame.winfo_children():
            child.destroy()
        self.rows.clear()

        by_category = {}
        for script in scripts:
            by_category.setdefault(script.get("category", "GENERAL"), []).append(script)

        for category in sorted(by_category):
            group = ttk.LabelFrame(self.features_frame, text=category)
            group.pack(fill="x", padx=4, pady=4)
            for script in sorted(by_category[category], key=lambda s: s.get("label", s["name"])):
                row = FeatureRow(group, script, self._send_command)
                self.rows[script["name"]] = row

        self._log_line(f"UI montada: {len(scripts)} scripts em {len(by_category)} categorias.", "in")

    # ---------------------------------------------------------------- events

    def _poll_events(self):
        try:
            while True:
                kind, payload, extra = self.events.get_nowait()
                if kind == "log":
                    self._log_line(payload, extra or "in")
                elif kind == "connected":
                    self.status.config(text="conectado", foreground="#2e7d32")
                    self.connect_btn.config(text="Disconnect")
                elif kind == "disconnected":
                    self.status.config(text="desconectado", foreground="#b00")
                    self.connect_btn.config(text="Connect")
                elif kind == "message":
                    self._handle_message(payload)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _handle_message(self, msg: dict):
        mtype = msg.get("type")
        if mtype == "welcome":
            self._log_line(f"<- welcome: {msg.get('game')} v{msg.get('version')}", "in")
        elif mtype == "manifest":
            self._rebuild_ui(msg.get("scripts", []))
        elif mtype == "state":
            # snapshot tambem carrega manifests; usa se a UI ainda esta vazia
            scripts = msg.get("scripts") or []
            if scripts and not self.rows:
                self._rebuild_ui(scripts)
            for name, info in (msg.get("features") or {}).items():
                if name in self.rows:
                    self.rows[name].set_state(int(info.get("state", 0)))
        elif mtype == "ack":
            feature = msg.get("feature")
            if feature in self.rows:
                self.rows[feature].set_state(int(msg.get("state", 0)))
            self._log_line(f"<- ack {feature} state={msg.get('state')}", "in")
        elif mtype == "error":
            self._log_line("<- erro: " + str(msg.get("message")), "err")
        elif mtype == "watch_update":
            details = f" | {msg.get('details')}" if msg.get("details") else ""
            self._log_line(
                f"<- watch [{msg.get('feature')}] {msg.get('name')} = {msg.get('value')}{details}",
                "in")
        elif mtype == "script_error":
            self._log_line(
                f"<- erro em {msg.get('feature')}: {msg.get('message')} (linha {msg.get('line')})",
                "err")
        else:
            self._log_line("<- " + json.dumps(msg)[:200], "in")

    def _log_line(self, text: str, tag: str):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n", tag)
        self.log.see("end")
        self.log.config(state="disabled")


def main():
    parser = argparse.ArgumentParser(description="Auto Trainer UI (manifest-driven)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=27015)
    parser.add_argument("--token", default="")
    options = parser.parse_args()

    root = tk.Tk()
    AutoTrainerApp(root, options.host, options.port, options.token)
    root.mainloop()


if __name__ == "__main__":
    main()
