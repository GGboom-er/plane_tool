#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Simplified UI for sending commands to running Maya or Blender processes."""

import sys
import socket
import subprocess
from dataclasses import dataclass

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit
)


@dataclass
class DCCProcess:
    proc_type: str
    pid: int
    port: int

    def __str__(self) -> str:
        return f"{self.proc_type} {self.pid} (port {self.port})"


def scan_dcc_processes():
    """Find running Maya or Blender processes via the system `ps` command."""
    processes = []
    try:
        output = subprocess.check_output(["ps", "-A", "-o", "pid=,comm="], text=True)
    except Exception:
        return processes

    maya_count = 0
    blender_count = 0
    for line in output.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        pid_str, name = parts
        name_lower = name.lower()
        if "maya" in name_lower:
            maya_count += 1
            port = 7000 + maya_count
            processes.append(DCCProcess("Maya", int(pid_str), port))
        elif "blender" in name_lower:
            blender_count += 1
            port = 7100 + blender_count
            processes.append(DCCProcess("Blender", int(pid_str), port))
    return processes


def send_command(proc: DCCProcess, command: str) -> str:
    """Send a Python command string to the given DCC process via socket."""
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
        result = send_command(proc, "print('hello from Blender')")
        self.log.append(result)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
    'test'