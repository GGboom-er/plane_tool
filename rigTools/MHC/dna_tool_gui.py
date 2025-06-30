import sys
import maya.cmds as cmds
from PySide6 import QtWidgets, QtCore, QtGui

# --- Module Reloading ---
# It's good practice in Maya to ensure the latest version of your modules are used.
script_dir = "Y:/GGbommer/scripts/plane_tool"
if script_dir not in sys.path:
    sys.path.append(script_dir)

try:
    import importlib
    # Ensure the utility module is reloaded for development
    if 'rigTools.MHC.dna_editor_utils' in sys.modules:
        importlib.reload(sys.modules['rigTools.MHC.dna_editor_utils'])
    from rigTools.MHC import dna_editor_utils
except ImportError as e:
    cmds.error(f"Failed to import dna_editor_utils: {e}")
    dna_editor_utils = None

class DNAToolGUI(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(DNAToolGUI, self).__init__(parent)
        self.setWindowTitle("MetaHuman DNA Editor")
        self.setMinimumSize(500, 400)

        self.dna_binary_reader = None
        self.dna_calibrated_reader = None
        self.selection_job = None

        self.create_widgets()
        self.create_layouts()
        self.create_connections()
        self.start_selection_job()

    def create_widgets(self):
        # --- Main Widgets ---
        self.load_dna_button = QtWidgets.QPushButton("Load DNA File")
        self.dna_path_line_edit = QtWidgets.QLineEdit()
        self.dna_path_line_edit.setPlaceholderText("No DNA file loaded")
        self.dna_path_line_edit.setReadOnly(True)

        self.tab_widget = QtWidgets.QTabWidget()

        # --- DNA BlendShapes Tab ---
        self.dna_bs_tab = QtWidgets.QWidget()
        self.dna_bs_filter_edit = QtWidgets.QLineEdit()
        self.dna_bs_filter_edit.setPlaceholderText("Filter BlendShapes...")
        self.dna_bs_list_widget = QtWidgets.QListWidget()
        self.dna_bs_list_widget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)

        # --- Controller Expressions Tab ---
        self.controller_tab = QtWidgets.QWidget()
        self.controller_filter_edit = QtWidgets.QLineEdit()
        self.controller_filter_edit.setPlaceholderText("Filter by Controller or BlendShape...")
        self.controller_list_widget = QtWidgets.QListWidget()
        self.controller_list_widget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.refresh_button.setToolTip("Manually refresh the list from the current selection.")

        # --- Status Bar ---
        self.status_bar = QtWidgets.QStatusBar()
        self.status_bar.showMessage("Ready.")

    def create_layouts(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        # --- Top Layout for DNA file loading ---
        load_layout = QtWidgets.QHBoxLayout()
        load_layout.addWidget(self.load_dna_button)
        load_layout.addWidget(self.dna_path_line_edit)
        main_layout.addLayout(load_layout)

        # --- DNA BlendShapes Tab Layout ---
        dna_bs_layout = QtWidgets.QVBoxLayout(self.dna_bs_tab)
        dna_bs_layout.addWidget(self.dna_bs_filter_edit)
        dna_bs_layout.addWidget(self.dna_bs_list_widget)
        self.tab_widget.addTab(self.dna_bs_tab, "All DNA BlendShapes")

        # --- Controller Expressions Tab Layout ---
        controller_layout = QtWidgets.QVBoxLayout(self.controller_tab)
        controller_layout.addWidget(self.controller_filter_edit)
        controller_layout.addWidget(self.controller_list_widget)
        controller_layout.addWidget(self.refresh_button)
        self.tab_widget.addTab(self.controller_tab, "Controller Driven Expressions")

        main_layout.addWidget(self.tab_widget)
        main_layout.addWidget(self.status_bar)

    def create_connections(self):
        self.load_dna_button.clicked.connect(self.load_dna_file)
        self.refresh_button.clicked.connect(self.update_controller_list)

        # Filter connections
        self.dna_bs_filter_edit.textChanged.connect(self.filter_dna_bs_list)
        self.controller_filter_edit.textChanged.connect(self.filter_controller_list)

        # List selection connections
        self.controller_list_widget.itemClicked.connect(self.on_controller_item_clicked)

    def start_selection_job(self):
        """Creates and starts the Maya scriptJob."""
        if self.selection_job is None:
            # parent to the dialog to ensure it's killed when the dialog is closed
            self.selection_job = cmds.scriptJob(
                event=["SelectionChanged", self.update_controller_list],
                protected=True,
                parent=self.objectName() # Attach job to this widget
            )

    def stop_selection_job(self):
        """Kills the Maya scriptJob if it exists."""
        if self.selection_job and cmds.scriptJob(exists=self.selection_job):
            cmds.scriptJob(kill=self.selection_job, force=True)
            self.selection_job = None

    def closeEvent(self, event):
        """Ensures the scriptJob is killed when the dialog is closed."""
        self.stop_selection_job()
        super(DNAToolGUI, self).closeEvent(event)

    def load_dna_file(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select DNA File", "", "DNA Files (*.dna);;All Files (*)")
        if not file_path:
            return

        self.dna_path_line_edit.setText(file_path)
        self.status_bar.showMessage(f"Loading {os.path.basename(file_path)}...")

        reader, calib_reader, error = dna_editor_utils.load_dna_for_editing_and_calib(file_path)
        if error:
            self.dna_binary_reader = None
            self.dna_calibrated_reader = None
            self.show_error_message("DNA Load Error", error)
            self.status_bar.showMessage("Failed to load DNA file.")
        else:
            self.dna_binary_reader = reader
            self.dna_calibrated_reader = calib_reader
            self.status_bar.showMessage("DNA file loaded successfully.")
            self.update_dna_bs_list()

    def update_dna_bs_list(self):
        self.dna_bs_list_widget.clear()
        if self.dna_binary_reader:
            blend_shape_names = dna_editor_utils.list_blend_shape_names(self.dna_binary_reader)
            if blend_shape_names:
                self.dna_bs_list_widget.addItems(blend_shape_names)
            else:
                self.dna_bs_list_widget.addItem("No BlendShapes found in DNA file.")
        else:
            self.dna_bs_list_widget.addItem("No DNA file loaded.")
        self.filter_dna_bs_list()

    def update_controller_list(self):
        self.controller_list_widget.clear()
        expression_info, warning = dna_editor_utils.get_expression_info_from_controller()

        if warning:
            self.status_bar.showMessage(warning)
            # Optionally, add a placeholder item to the list
            item = QtWidgets.QListWidgetItem(warning)
            item.setForeground(QtGui.QColor('gray'))
            self.controller_list_widget.addItem(item)
            return

        if not expression_info:
            self.status_bar.showMessage("Selected object(s) do not drive any BlendShapes.")
            return

        self.status_bar.showMessage(f"Found expressions for {len(expression_info)} controller(s).")
        for controller, bs_info_list in expression_info.items():
            # Add the controller as a non-selectable header item
            controller_item = QtWidgets.QListWidgetItem(controller)
            controller_item.setFlags(controller_item.flags() & ~QtCore.Qt.ItemIsSelectable)
            font = controller_item.font()
            font.setBold(True)
            controller_item.setFont(font)
            self.controller_list_widget.addItem(controller_item)

            if bs_info_list:
                for bs_info in bs_info_list:
                    # Add the blendshape info as a selectable item
                    bs_item_text = f"  - {bs_info['blendShapeNode']}.{bs_info['blendShapeTargetAttr']}"
                    bs_item = QtWidgets.QListWidgetItem(bs_item_text)
                    bs_item.setData(QtCore.Qt.UserRole, controller) # Store controller name in the item
                    self.controller_list_widget.addItem(bs_item)
            else:
                no_bs_item = QtWidgets.QListWidgetItem("  - No BlendShapes driven by this controller.")
                no_bs_item.setFlags(no_bs_item.flags() & ~QtCore.Qt.ItemIsSelectable)
                no_bs_item.setForeground(QtGui.QColor('gray'))
                self.controller_list_widget.addItem(no_bs_item)
        
        self.filter_controller_list()

    def filter_list_widget(self, list_widget, filter_text):
        """Generic function to filter a QListWidget."""
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            # Only hide selectable items, keep headers visible
            if item.flags() & QtCore.Qt.ItemIsSelectable:
                item.setHidden(filter_text.lower() not in item.text().lower())

    def filter_dna_bs_list(self):
        self.filter_list_widget(self.dna_bs_list_widget, self.dna_bs_filter_edit.text())

    def filter_controller_list(self):
        filter_text = self.controller_filter_edit.text().lower()
        for i in range(self.controller_list_widget.count()):
            item = self.controller_list_widget.item(i)
            # For controllers, we need a more complex logic to hide the header if all its children are hidden
            # This is a simplified version that just filters the text content.
            item.setHidden(filter_text not in item.text().lower())


    def on_controller_item_clicked(self, item):
        """Selects the corresponding controller in Maya when an item is clicked."""
        controller_name = item.data(QtCore.Qt.UserRole)
        if controller_name and cmds.objExists(controller_name):
            cmds.select(controller_name, replace=True)
            self.status_bar.showMessage(f"Selected '{controller_name}' in Maya.")

    def show_error_message(self, title, message):
        """Displays an error message in a dialog box."""
        msg_box = QtWidgets.QMessageBox(self)
        msg_box.setIcon(QtWidgets.QMessageBox.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec_()

def show_dna_tool_gui():
    # Ensure dna_editor_utils was imported correctly
    if dna_editor_utils is None:
        cmds.error("Cannot show GUI because dna_editor_utils failed to load.")
        return

    # Close any existing instances of the dialog
    for widget in QtWidgets.QApplication.instance().allWidgets():
        if isinstance(widget, DNAToolGUI):
            widget.close()
            widget.deleteLater()

    # Create and show the dialog
    # Make it a global variable to prevent it from being garbage collected
    global dna_tool_dialog
    maya_main_window = next(w for w in QtWidgets.QApplication.instance().allWidgets() if w.objectName() == 'MayaWindow')
    dna_tool_dialog = DNAToolGUI(parent=maya_main_window)
    dna_tool_dialog.setObjectName("DNAToolGUI_instance") # Set a unique name for parenting the scriptJob
    dna_tool_dialog.show()

# --- How to run in Maya ---
# import sys
# script_dir = "Y:/GGbommer/scripts/plane_tool"
# if script_dir not in sys.path:
#     sys.path.append(script_dir)
#
# from rigTools.MHC import dna_tool_gui
# dna_tool_gui.show_dna_tool_gui()

if __name__ == "__main__":
    print("This script is intended to be run within Maya.")
    print("Execute the 'How to run' code block in Maya's script editor.")
