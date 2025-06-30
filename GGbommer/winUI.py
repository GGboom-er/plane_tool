#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Simplified UI for sending commands to running Maya or Blender processes."""

import sys
import socket
import subprocess
import json
from dataclasses import dataclass
from pathlib import Path

try:
    import psutil  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    psutil = None

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit
)


@dataclass
class DCCProcess:
    proc_type: str
    pid: int
    port: int | None = None

    def __str__(self) -> str:
        port_info = self.port if self.port is not None else "N/A"
        return f"{self.proc_type} {self.pid} (port {port_info})"


PORT_MAP_FILE = Path(__file__).resolve().parent.parent / "dcc_port_map.json"


def load_port_map() -> dict[int, int]:
    try:
        with open(PORT_MAP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {int(pid): int(port) for pid, port in data.items()}
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def scan_dcc_processes():
    """Find running Maya or Blender processes, using psutil if available."""
    processes: list[DCCProcess] = []
    port_map = load_port_map()

    if psutil is not None:
        try:
            for p in psutil.process_iter(["pid", "name"]):
                name = (p.info.get("name") or "").lower()
                if "maya" in name:
                    proc_type = "Maya"
                elif "blender" in name:
                    proc_type = "Blender"
                else:
                    continue
                pid = p.info["pid"]
                port = port_map.get(pid)
                processes.append(DCCProcess(proc_type, pid, port))
        except Exception:
            pass
    else:
        # Fallback to simple command line scanning
        try:
            if sys.platform.startswith("win"):
                output = subprocess.check_output(["tasklist", "/FO", "CSV"], text=True, encoding="utf-8", errors="ignore")
                lines = output.strip().splitlines()[1:]
                for line in lines:
                    fields = [f.strip('"') for f in line.split(',')]
                    if len(fields) < 2:
                        continue
                    name, pid_str = fields[0], fields[1]
                    name_lower = name.lower()
                    pid = int(pid_str)
                    if "maya" in name_lower:
                        processes.append(DCCProcess("Maya", pid, port_map.get(pid)))
                    elif "blender" in name_lower:
                        processes.append(DCCProcess("Blender", pid, port_map.get(pid)))
            else:
                output = subprocess.check_output(["ps", "-A", "-o", "pid=,comm="], text=True)
                for line in output.splitlines():
                    parts = line.strip().split(None, 1)
                    if len(parts) != 2:
                        continue
                    pid_str, name = parts
                    name_lower = name.lower()
                    pid = int(pid_str)
                    if "maya" in name_lower:
                        processes.append(DCCProcess("Maya", pid, port_map.get(pid)))
                    elif "blender" in name_lower:
                        processes.append(DCCProcess("Blender", pid, port_map.get(pid)))
        except Exception:
            pass
    return processes


def send_command(proc: DCCProcess, command: str) -> str:
    """Send a Python command string to the given DCC process via socket."""
    if proc.port is None:
        return f"No known port for {proc}"
    try:
        with socket.create_connection(("127.0.0.1", proc.port), timeout=2) as sock:
            sock.sendall(command.encode("utf-8"))
        return f"Sent to {proc}"
    except Exception as exc:
        return f"Failed sending to {proc}: {exc}"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Maya & Blender Interface")
        self.setGeometry(200, 200, 400, 300)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.proc_box = QComboBox()
        layout.addWidget(QLabel("Select DCC Process:"))
        layout.addWidget(self.proc_box)

        self.maya_btn = QPushButton("Print from Maya")
        self.blender_btn = QPushButton("Print from Blender")
        layout.addWidget(self.maya_btn)
        layout.addWidget(self.blender_btn)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        self.maya_btn.clicked.connect(self.on_maya_clicked)
        self.blender_btn.clicked.connect(self.on_blender_clicked)

        self.refresh_processes()

    def refresh_processes(self):
        self.processes = scan_dcc_processes()
        self.proc_box.clear()
        for proc in self.processes:
            self.proc_box.addItem(str(proc), proc)

    def current_process(self) -> DCCProcess | None:
        idx = self.proc_box.currentIndex()
        if 0 <= idx < len(self.processes):
            return self.processes[idx]
        return None

    def on_maya_clicked(self):
        proc = self.current_process()
        if proc is None:
            self.log.append("No process selected")
            return
        if proc.proc_type != "Maya":
            self.log.append("Selected process is not Maya")
            return
        if proc.port is None:
            self.log.append(f"Port for {proc} is unknown")
            return
        result = send_command(proc, "print('hello from Maya')")
        self.log.append(result)

    def on_blender_clicked(self):
        proc = self.current_process()
        if proc is None:
            self.log.append("No process selected")
            return
        if proc.proc_type != "Blender":
            self.log.append("Selected process is not Blender")
            return
        if proc.port is None:
            self.log.append(f"Port for {proc} is unknown")
            return
        result = send_command(proc, "print('hello from Blender')")
        self.log.append(result)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
