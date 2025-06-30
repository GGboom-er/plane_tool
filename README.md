# plane_tool

This repository collects various tools for Maya, Blender and other DCC software.
The `GGbommer` package contains a simple PyQt5 interface demonstrating how to
send Python commands to running DCC processes.

## Requirements
- Python 3
- PyQt5
- Running instances of Maya or Blender listening on command ports

## Running the demo UI
```
python GGbommer/winUI.py
```
The application scans processes via `ps` and lists detected Maya/Blender
instances in a drop-down menu. Select a process and press the corresponding
button to send a `print` command to that application. The command is delivered
via a TCP socket using ports `700x` for Maya and `710x` for Blender.
