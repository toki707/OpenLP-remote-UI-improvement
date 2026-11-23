# -*- coding: utf-8 -*-

##########################################################################
# OpenLP - Open Source Lyrics Projection                                 #
# ---------------------------------------------------------------------- #
# Copyright (c) 2008-2024 OpenLP Developers                              #
# ---------------------------------------------------------------------- #
# This program is free software: you can redistribute it and/or modify   #
# it under the terms of the GNU General Public License as published by   #
# the Free Software Foundation, either version 3 of the License, or      #
# (at your option) any later version.                                    #
#                                                                        #
# This program is distributed in the hope that it will be useful,        #
# but WITHOUT ANY WARRANTY; without even the implied warranty of         #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
# GNU General Public License for more details.                           #
#                                                                        #
# You should have received a copy of the GNU General Public License      #
# along with this program.  If not, see <https://www.gnu.org/licenses/>. #
##########################################################################
"""
Simplified Youth/Church Mode & Live Dark/Light Theme Switcher for OpenLP Desktop UI.
"""
import logging
from PyQt5 import QtCore, QtGui, QtWidgets

from openlp.core.common.registry import Registry
from openlp.core.lib.plugin import PluginStatus
from openlp.core.state import State

log = logging.getLogger(__name__)

YOUTH_ALLOWED_PLUGINS = ('bibles', 'images', 'custom', 'songs')

MODERN_DARK_QSS = """
QMainWindow, QDialog {
    background-color: #000000;
    color: #F5F5F7;
    font-family: "Segoe UI", -apple-system, sans-serif;
}
QMenuBar {
    background-color: #1C1C1E;
    color: #F5F5F7;
    border-bottom: 1px solid #38383A;
    padding: 2px 6px;
}
QMenuBar::item:selected, QMenu::item:selected {
    background-color: #0A84FF;
    color: #FFFFFF;
    border-radius: 6px;
}
QDockWidget {
    color: #98989D;
    font-weight: 600;
}
QDockWidget::title {
    background-color: #1C1C1E;
    border: 1px solid #38383A;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    padding: 7px 12px;
    color: #F5F5F7;
}
QToolBar#simplified_quick_bar {
    background-color: #1C1C1E;
    border-bottom: 1px solid #38383A;
    padding: 8px 14px;
    spacing: 8px;
}
QToolBar#simplified_quick_bar QPushButton {
    background-color: #2C2C2E;
    color: #F5F5F7;
    border: none;
    border-radius: 15px;
    padding: 6px 16px;
    font-weight: 600;
}
QToolBar#simplified_quick_bar QPushButton:hover {
    background-color: #3A3A3C;
}
QToolBar#simplified_quick_bar QPushButton:checked {
    background-color: #0A84FF;
    color: #FFFFFF;
}
QToolBox::tab {
    background-color: #1C1C1E;
    color: #F5F5F7;
    border: 1px solid #38383A;
    border-radius: 8px;
    padding: 6px 12px;
    font-weight: 600;
}
QToolBox::tab:selected {
    background-color: #0A84FF;
    color: #FFFFFF;
    border-color: #0A84FF;
}
QListWidget, QTreeWidget, QTableWidget {
    background-color: #1C1C1E;
    color: #F5F5F7;
    border: 1px solid #38383A;
    border-radius: 10px;
    padding: 4px;
    selection-background-color: #0A84FF;
    selection-color: #FFFFFF;
    outline: none;
}
QListWidget::item, QTreeWidget::item {
    padding: 6px 8px;
    border-radius: 6px;
}
QListWidget::item:selected, QTreeWidget::item:selected {
    background-color: #0A84FF;
    color: #FFFFFF;
}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
    background-color: #1C1C1E;
    color: #F5F5F7;
    border: 1px solid #38383A;
    border-radius: 8px;
    padding: 5px 10px;
    selection-background-color: #0A84FF;
    selection-color: #FFFFFF;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1.5px solid #0A84FF;
}
QPushButton, QToolButton {
    background-color: #2C2C2E;
    color: #F5F5F7;
    border: 1px solid #38383A;
    border-radius: 8px;
    padding: 5px 12px;
    font-weight: 500;
}
QPushButton:hover, QToolButton:hover {
    background-color: #3A3A3C;
}
QPushButton:checked, QToolButton:checked {
    background-color: #0A84FF;
    border-color: #0A84FF;
    color: #FFFFFF;
}
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #48484A;
    min-height: 24px;
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

MODERN_LIGHT_QSS = """
QMainWindow, QDialog {
    background-color: #F2F2F7;
    color: #1D1D1F;
    font-family: "Segoe UI", -apple-system, sans-serif;
}
QMenuBar {
    background-color: #F9F9FB;
    color: #1D1D1F;
    border-bottom: 1px solid #E5E5EA;
    padding: 2px 6px;
}
QMenuBar::item:selected, QMenu::item:selected {
    background-color: #007AFF;
    color: #FFFFFF;
    border-radius: 6px;
}
QDockWidget {
    color: #6E6E73;
    font-weight: 600;
}
QDockWidget::title {
    background-color: #FFFFFF;
    border: 1px solid #E5E5EA;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    padding: 7px 12px;
    color: #1D1D1F;
}
QToolBar#simplified_quick_bar {
    background-color: #F9F9FB;
    border-bottom: 1px solid #E5E5EA;
    padding: 8px 14px;
    spacing: 8px;
}
QToolBar#simplified_quick_bar QPushButton {
    background-color: #E5E5EA;
    color: #1D1D1F;
    border: none;
    border-radius: 15px;
    padding: 6px 16px;
    font-weight: 600;
}
QToolBar#simplified_quick_bar QPushButton:hover {
    background-color: #D1D1D6;
}
QToolBar#simplified_quick_bar QPushButton:checked {
    background-color: #007AFF;
    color: #FFFFFF;
}
QToolBox::tab {
    background-color: #FFFFFF;
    color: #1D1D1F;
    border: 1px solid #E5E5EA;
    border-radius: 8px;
    padding: 6px 12px;
    font-weight: 600;
}
QToolBox::tab:selected {
    background-color: #007AFF;
    color: #FFFFFF;
    border-color: #007AFF;
}
QListWidget, QTreeWidget, QTableWidget {
    background-color: #FFFFFF;
    color: #1D1D1F;
    border: 1px solid #E5E5EA;
    border-radius: 10px;
    padding: 4px;
    selection-background-color: #007AFF;
    selection-color: #FFFFFF;
    outline: none;
}
QListWidget::item, QTreeWidget::item {
    padding: 6px 8px;
    border-radius: 6px;
}
QListWidget::item:selected, QTreeWidget::item:selected {
    background-color: #007AFF;
    color: #FFFFFF;
}
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
    background-color: #FFFFFF;
    color: #1D1D1F;
    border: 1px solid #D1D1D6;
    border-radius: 8px;
    padding: 5px 10px;
    selection-background-color: #007AFF;
    selection-color: #FFFFFF;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus {
    border: 1.5px solid #007AFF;
}
QPushButton, QToolButton {
    background-color: #FFFFFF;
    color: #1D1D1F;
    border: 1px solid #D1D1D6;
    border-radius: 8px;
    padding: 5px 12px;
    font-weight: 500;
}
QPushButton:hover, QToolButton:hover {
    background-color: #F2F2F7;
}
QPushButton:checked, QToolButton:checked {
    background-color: #007AFF;
    border-color: #007AFF;
    color: #FFFFFF;
}
QScrollBar:vertical {
    background: transparent;
    width: 8px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #C7C7CC;
    min-height: 24px;
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""


class SimplifiedModeController(QtCore.QObject):
    """
    Attaches a clear quick-access header toolbar to the OpenLP MainWindow for youth/church operators.
    Provides 1-click access to Bible, Images, Custom Slides, and Songs, a Simplified/Full mode toggle,
    and a live Dark/Light theme toggle while preserving every tab's native Preview and Direct Live buttons.
    """
    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.is_simple_mode = False
        self.is_dark_theme = True
        self.quick_buttons = {}
        self.setup_toolbar()

    def setup_toolbar(self):
        self.toolbar = QtWidgets.QToolBar('Accès Rapide Culte', self.main_window)
        self.toolbar.setObjectName('simplified_quick_bar')
        self.toolbar.setMovable(False)
        self.toolbar.setFloatable(False)

        label = QtWidgets.QLabel(' Bibliothèque : ', self.toolbar)
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        self.toolbar.addWidget(label)

        tabs = [
            ('bibles', 'Bible'),
            ('images', 'Images & Affiches'),
            ('custom', 'Diapos perso'),
            ('songs', 'Chants'),
        ]
        for plugin_name, title in tabs:
            btn = QtWidgets.QPushButton(title, self.toolbar)
            btn.setCheckable(True)
            btn.setCursor(QtCore.Qt.PointingHandCursor)
            btn.setMinimumHeight(32)
            btn.clicked.connect(lambda checked, p=plugin_name: self.focus_plugin_tab(p))
            self.toolbar.addWidget(btn)
            self.quick_buttons[plugin_name] = btn

        spacer = QtWidgets.QWidget(self.toolbar)
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
        self.toolbar.addWidget(spacer)

        self.simple_mode_btn = QtWidgets.QPushButton('Mode Simplifié (Jeunes) : Désactivé', self.toolbar)
        self.simple_mode_btn.setCheckable(True)
        self.simple_mode_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.simple_mode_btn.setMinimumHeight(32)
        self.simple_mode_btn.clicked.connect(self.toggle_simple_mode)
        self.toolbar.addWidget(self.simple_mode_btn)

        self.theme_btn = QtWidgets.QPushButton('Thème : Noir / Blanc', self.toolbar)
        self.theme_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self.theme_btn.setMinimumHeight(32)
        self.theme_btn.clicked.connect(self.toggle_color_theme)
        self.toolbar.addWidget(self.theme_btn)

        self.main_window.addToolBar(QtCore.Qt.TopToolBarArea, self.toolbar)
        self.main_window.setStyleSheet(MODERN_LIGHT_QSS)
        if hasattr(self.main_window, 'media_manager_dock') and self.main_window.media_manager_dock:
            self.main_window.media_manager_dock.setStyleSheet('')

    def focus_plugin_tab(self, plugin_name: str):
        if not self.main_window.media_manager_dock.isVisible():
            self.main_window.media_manager_dock.setVisible(True)
        toolbox = self.main_window.media_tool_box
        for idx in range(toolbox.count()):
            widget = toolbox.widget(idx)
            if widget and getattr(widget, 'settings_section', '') == plugin_name:
                toolbox.setCurrentIndex(idx)
                break
        for name, btn in self.quick_buttons.items():
            btn.setChecked(name == plugin_name)

    def toggle_simple_mode(self):
        self.is_simple_mode = self.simple_mode_btn.isChecked()
        if self.is_simple_mode:
            self.simple_mode_btn.setText('Mode Simplifié (Jeunes) : Actif')
            if hasattr(self.main_window, 'projector_manager_dock'):
                self.main_window.projector_manager_dock.setVisible(False)
            for plugin in State().list_plugins():
                if plugin and plugin.media_item and plugin.name not in YOUTH_ALLOWED_PLUGINS:
                    self.main_window.media_dock_manager.remove_dock(plugin.media_item)
            self.focus_plugin_tab('bibles')
        else:
            self.simple_mode_btn.setText('Mode Simplifié (Jeunes) : Désactivé')
            for plugin in State().list_plugins():
                if plugin and plugin.status == PluginStatus.Active and plugin.media_item:
                    self.main_window.media_dock_manager.add_item_to_dock(plugin.media_item)

    def toggle_color_theme(self):
        app = QtWidgets.QApplication.instance()
        if not app:
            return
        self.is_dark_theme = not self.is_dark_theme
        if self.is_dark_theme:
            from openlp.core.ui.style import set_default_darkmode
            set_default_darkmode(app)
            app.setStyleSheet(MODERN_DARK_QSS)
            self.main_window.setStyleSheet(MODERN_DARK_QSS)
            self.theme_btn.setText('Thème : Noir')
        else:
            from openlp.core.ui.style import set_default_lightmode
            set_default_lightmode(app)
            app.setStyleSheet(MODERN_LIGHT_QSS)
            self.main_window.setStyleSheet(MODERN_LIGHT_QSS)
            self.theme_btn.setText('Thème : Blanc')


def attach_simplified_mode(main_window):
    """
    Attach the SimplifiedModeController to the main window if not already attached.
    """
    if not hasattr(main_window, 'simplified_mode_controller'):
        main_window.simplified_mode_controller = SimplifiedModeController(main_window)
    return main_window.simplified_mode_controller
