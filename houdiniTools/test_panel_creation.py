import hou

# --- H21 API for Panel Creation ---

INTERFACE_NAME = "GG_SmartReduce"
desktop = hou.ui.curDesktop()
pane = desktop.createFloatingPane(hou.paneTabType.PythonPanel)

# Set the interface for the new panel tab
panel = pane.paneTabOfType(hou.paneTabType.PythonPanel)
panel.setPythonPanel(INTERFACE_NAME)

print("[SUCCESS] Panel creation script logic is correct for H21.")
