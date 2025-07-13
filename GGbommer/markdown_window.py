
import sys
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer, QPoint
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget, QTextEdit, QLabel,
    QPushButton, QSlider, QComboBox, QCheckBox, QRadioButton, QLineEdit,
    QGroupBox, QToolBox, QGraphicsOpacityEffect, QProgressBar, QMessageBox, QStyle,
    QSizePolicy
)

# --- 科技感、设计感十足的样式表 (Stylesheet) ---
STYLESHEET = """
QWidget {
    background-color: #1e1e2f;
    color: #e0e0ff;
    font-family: 'Microsoft YaHei', 'PingFang SC', 'Helvetica Neue', 'Arial', sans-serif;
    font-size: 15px;
}
/* 为主窗口和自定义标题栏设置一个特殊的属性，以便在样式表中定位 */
#MainWindow, #CustomTitleBar {
    background-color: #161625;
}
#CustomTitleBar {
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}
QListWidget {
    background-color: #2a2a40;
    border: none;
    padding: 10px;
    border-bottom-left-radius: 10px; /* 使其与主窗口圆角匹配 */
}
QListWidget::item {
    padding: 15px;
    margin: 5px 0;
    border-radius: 8px;
    color: #c0c0ff;
}
QListWidget::item:hover {
    background-color: #3a3a52;
}
QListWidget::item:selected {
    background-color: #0096ff;
    color: white;
    font-weight: bold;
}
QTextEdit, QLineEdit {
    background-color: #2a2a40;
    border: 1px solid #4a4a62;
    border-radius: 8px;
    padding: 10px;
    color: #e0e0ff;
}
QPushButton {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0096ff, stop:1 #005cff);
    color: white;
    border: none;
    padding: 12px 25px;
    border-radius: 8px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00aaff, stop:1 #007bff);
    border: 1px solid #00d2ff; /* 替换box-shadow，使用边框实现辉光效果 */
}
QPushButton:pressed {
    background-color: #005cff;
}
/* 自定义标题栏按钮 */
#TitleBarButton {
    background-color: transparent;
    border-radius: 10px;
    padding: 0;
    margin: 0;
    qproperty-iconSize: 18px 18px;
}
#TitleBarButton:hover {
    background-color: #3a3a52;
}
#CloseButton:hover {
    background-color: #e81123;
}
QGroupBox {
    font-weight: bold;
    color: #00d2ff;
    border: 1px solid #4a4a62;
    border-radius: 8px;
    margin-top: 10px;
    padding: 25px 15px 15px 15px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    left: 15px;
    background-color: #1e1e2f;
}
QSlider::groove:horizontal {
    border: 1px solid #4a4a62;
    height: 6px;
    background: #2a2a40;
    margin: 2px 0;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #0096ff;
    border: 2px solid white;
    width: 20px;
    margin: -8px 0;
    border-radius: 11px;
}
QComboBox {
    background-color: #2a2a40;
    border: 1px solid #4a4a62;
    border-radius: 8px;
    padding: 8px;
}
QComboBox::drop-down { border: none; }
QComboBox QAbstractItemView {
    background-color: #2a2a40;
    border: 1px solid #4a4a62;
    selection-background-color: #0096ff;
}
QToolBox::tab {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3a3a52, stop:1 #2a2a40);
    border-radius: 8px;
    padding: 10px;
    font-weight: bold;
    color: #c0c0ff;
}
QToolBox::tab:selected {
    background: #0096ff;
    color: white;
}
QProgressBar {
    border: 1px solid #4a4a62;
    border-radius: 8px;
    text-align: center;
    color: white;
    background-color: #2a2a40;
}
QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d2ff, stop:1 #0096ff);
    border-radius: 7px;
}
"""

# --- 自定义标题栏 ---
class CustomTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setObjectName("CustomTitleBar")
        self.setFixedHeight(40)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 5, 0)
        layout.setSpacing(10)

        # 窗口图标和标题
        icon_label = QLabel()
        icon = self.style().standardIcon(QStyle.SP_DesktopIcon)
        icon_label.setPixmap(icon.pixmap(24, 24))
        title_label = QLabel(parent.windowTitle())
        title_label.setStyleSheet("font-weight: bold; color: #e0e0ff;")

        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addStretch()

        # 窗口控制按钮
        self.min_button = self.create_button("SP_TitleBarMinButton", self.parent.showMinimized)
        self.max_button = self.create_button("SP_TitleBarMaxButton", self.toggle_maximize)
        self.close_button = self.create_button("SP_TitleBarCloseButton", self.parent.close)
        self.close_button.setObjectName("CloseButton") # 为关闭按钮设置特殊ID以便应用不同样式

        layout.addWidget(self.min_button)
        layout.addWidget(self.max_button)
        layout.addWidget(self.close_button)

        self.drag_position = None

    def create_button(self, icon_name, slot):
        button = QPushButton()
        button.setObjectName("TitleBarButton")
        button.setIcon(self.style().standardIcon(getattr(QStyle, icon_name)))
        button.clicked.connect(slot)
        button.setFixedSize(30, 30)
        return button

    def toggle_maximize(self):
        if self.parent.isMaximized():
            self.parent.showNormal()
        else:
            self.parent.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.parent.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position:
            self.parent.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_position = None
        event.accept()


# --- 带淡入淡出效果的QStackedWidget ---
class FadingStackedWidget(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.m_duration = 300

    def setCurrentIndex(self, index):
        if self.currentIndex() == index: return
        self.p_opacity = QPropertyAnimation(self, b"windowOpacity")
        self.p_opacity.setDuration(self.m_duration // 2)
        self.p_opacity.setStartValue(1.0)
        self.p_opacity.setEndValue(0.0)
        self.p_opacity.finished.connect(lambda: self._on_fade_out_finished(index))
        self.p_opacity.start()

    def _on_fade_out_finished(self, index):
        super().setCurrentIndex(index)
        self.p_opacity = QPropertyAnimation(self, b"windowOpacity")
        self.p_opacity.setDuration(self.m_duration)
        self.p_opacity.setStartValue(0.0)
        self.p_opacity.setEndValue(1.0)
        self.p_opacity.setEasingCurve(QEasingCurve.InOutQuad)
        self.p_opacity.start()

class UIMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setObjectName("MainWindow")
        self.setWindowTitle("高级UI工具展示")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground) # 使圆角生效
        self.setGeometry(100, 100, 1200, 800)

        # 创建一个带圆角的背景Widget
        container = QWidget()
        container.setStyleSheet("background-color: #161625; border-radius: 10px;")
        
        # 主布局
        outer_layout = QVBoxLayout(container)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # 添加自定义标题栏
        self.title_bar = CustomTitleBar(self)
        outer_layout.addWidget(self.title_bar)

        # 内容区布局
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # --- 左侧导航栏 ---
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(220)
        self.nav_list.setIconSize(QSize(24, 24))
        content_layout.addWidget(self.nav_list)

        # --- 右侧内容区 ---
        self.stack = FadingStackedWidget()
        content_layout.addWidget(self.stack)
        
        outer_layout.addLayout(content_layout)
        self.setCentralWidget(container)

        # --- 创建并添加页面 ---
        self.add_page("主页", "SP_ComputerIcon", self.create_home_page())
        self.add_page("交互控件", "SP_FileDialogDetailedView", self.create_controls_page())
        self.add_page("折叠面板", "SP_ToolBarHorizontalExtensionButton", self.create_toolbox_page())
        self.add_page("批量处理中心", "SP_CommandLink", self.create_batch_page())

        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav_list.setCurrentRow(0)

    def add_page(self, title, icon_name, widget):
        icon = self.style().standardIcon(getattr(QStyle, icon_name))
        item = QListWidgetItem(icon, f"  {title}")
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.nav_list.addItem(item)
        self.stack.addWidget(widget)

    def create_home_page(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        markdown_text = """
# 欢迎来到高级UI工具展示

本应用旨在演示一个功能丰富、设计现代的专业工具界面。

---

## 核心特性

*   **自定义窗口**: 拥有完整功能的自定义标题栏，支持拖动、最小化、最大化和关闭。
*   **动态交互**: 页面切换采用平滑的**淡入淡出**动画，提升用户体验。
*   **丰富控件**: 集成了滑块、下拉��单、折叠面板等多种常用及高级控件。
*   **实质功能**: “批量处理中心”模块模拟了真实世界中的工具流任务。
"""
        text_edit.setMarkdown(markdown_text)
        layout.addWidget(text_edit)
        return widget

    def create_controls_page(self):
        page_widget = QWidget()
        main_layout = QVBoxLayout(page_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        slider_group = QGroupBox("动态滑块调节")
        slider_layout = QHBoxLayout()
        slider = QSlider(Qt.Horizontal)
        slider_label = QLabel("数值: 50")
        slider_label.setFixedWidth(120)
        slider.setValue(50)
        slider.valueChanged.connect(lambda v: slider_label.setText(f"数值: {v}"))
        slider_layout.addWidget(slider)
        slider_layout.addWidget(slider_label)
        slider_group.setLayout(slider_layout)
        main_layout.addWidget(slider_group)
        combo_group = QGroupBox("数据源选择")
        combo_layout = QVBoxLayout()
        combo = QComboBox()
        combo.addItems(["角色模型 (Character Rig)", "场景文件 (Scene File)", "动画缓存 (Animation Cache)", "贴图文件 (Texture)"])
        combo_label = QLabel("当前选择: 角色模型 (Character Rig)")
        combo.currentTextChanged.connect(lambda t: combo_label.setText(f"当前选择: {t}"))
        combo_layout.addWidget(combo)
        combo_layout.addWidget(combo_label)
        combo_group.setLayout(combo_layout)
        main_layout.addWidget(combo_group)
        check_radio_group = QGroupBox("参数配置")
        check_radio_layout = QHBoxLayout()
        check_vbox = QVBoxLayout()
        check_vbox.addWidget(QLabel("附加功能:"))
        check_vbox.addWidget(QCheckBox("启用IK/FK匹配"))
        check_vbox.addWidget(QCheckBox("加载高清代理"))
        radio_vbox = QVBoxLayout()
        radio_vbox.addWidget(QLabel("处理精度:"))
        radio1 = QRadioButton("标准模式")
        radio2 = QRadioButton("高精度模式")
        radio1.setChecked(True)
        radio_vbox.addWidget(radio1)
        radio_vbox.addWidget(radio2)
        check_radio_layout.addLayout(check_vbox)
        check_radio_layout.addSpacing(50)
        check_radio_layout.addLayout(radio_vbox)
        check_radio_group.setLayout(check_radio_layout)
        main_layout.addWidget(check_radio_group)
        main_layout.addStretch()
        return page_widget

    def create_toolbox_page(self):
        page_widget = QWidget()
        main_layout = QVBoxLayout(page_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)
        tool_box = QToolBox()
        main_layout.addWidget(tool_box)
        proj_widget = QWidget()
        proj_layout = QVBoxLayout(proj_widget)
        proj_layout.addWidget(QLabel("项目名称:"))
        proj_layout.addWidget(QLineEdit("大型科幻电影项目"))
        proj_layout.addWidget(QPushButton("保存项目设置"))
        proj_layout.addStretch()
        tool_box.addItem(proj_widget, "项目设置")
        user_widget = QWidget()
        user_layout = QVBoxLayout(user_widget)
        user_layout.addWidget(QCheckBox("启用自动保存 (每10分钟)"))
        user_layout.addWidget(QCheckBox("启动时显示欢迎屏幕"))
        user_layout.addStretch()
        tool_box.addItem(user_widget, "用户偏好")
        adv_widget = QWidget()
        adv_layout = QVBoxLayout(adv_widget)
        adv_layout.addWidget(QLabel("警告: 以下为开发者选项。"))
        adv_layout.addWidget(QPushButton("重置为出厂设置"))
        adv_layout.addStretch()
        tool_box.addItem(adv_widget, "高级选项")
        return page_widget

    def create_batch_page(self):
        page_widget = QWidget()
        main_layout = QVBoxLayout(page_widget)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        file_group = QGroupBox("文件选择")
        file_layout = QVBoxLayout(file_group)
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit("/path/to/your/assets/characters/")
        browse_btn = QPushButton("浏览...")
        browse_btn.setFixedWidth(120)
        browse_btn.clicked.connect(self.populate_files)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(browse_btn)
        self.file_list = QListWidget()
        file_layout.addLayout(path_layout)
        file_layout.addWidget(self.file_list)
        main_layout.addWidget(file_group)
        process_group = QGroupBox("处理选项")
        process_layout = QVBoxLayout(process_group)
        process_layout.addWidget(QCheckBox("覆盖现有文件"))
        process_layout.addWidget(QCheckBox("为原文件创建备份 (.bak)"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        start_btn = QPushButton("开始处理")
        start_btn.clicked.connect(self.start_processing)
        process_layout.addWidget(self.progress_bar)
        process_layout.addWidget(start_btn, 0, Qt.AlignRight)
        main_layout.addWidget(process_group)
        return page_widget

    def populate_files(self):
        self.file_list.clear()
        dummy_files = ["hero_main_rig_v021.ma", "villain_heavy_rig_v009.ma", "sidekick_small_rig_v012.ma", "boss_final_rig_v005.ma", "npc_female_generic_rig_v030.ma", "npc_male_generic_rig_v028.ma"]
        for f in dummy_files:
            self.file_list.addItem(QListWidgetItem(self.style().standardIcon(QStyle.SP_FileIcon), f))

    def start_processing(self):
        if self.file_list.count() == 0:
            QMessageBox.warning(self, "警告", "文件列表为空，请先浏览文件。")
            return
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_value = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(50)

    def update_progress(self):
        self.progress_value += 1
        self.progress_bar.setValue(self.progress_value)
        if self.progress_value >= 100:
            self.timer.stop()
            self.progress_bar.setVisible(False)
            QMessageBox.information(self, "完成", "所有文件已成功处理！")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    window = UIMainWindow()
    window.show()
    sys.exit(app.exec())
