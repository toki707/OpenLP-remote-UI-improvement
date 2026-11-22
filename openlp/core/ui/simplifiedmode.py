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
    background-color: #0f1115;
    color: #f3f4f6;
}
QDockWidget {
    color: #f3f4f6;
    font-weight: 600;
}
QDockWidget::title {
    background-color: #161920;
    border: 1px solid #2a2f3a;
    border-radius: 4px;
    padding: 6px 10px;
}
QToolBar#simplified_quick_bar {
    background-color: #161920;
    border-bottom: 1px solid #2a2f3a;
    padding: 6px 10px;
    spacing: 6px;
}
QListWidget, QTreeWidget, QTableWidget, QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
    background-color: #161920;
    color: #f3f4f6;
    border: 1px solid #2a2f3a;
    border-radius: 6px;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}
QPushButton, QToolButton {
    background-color: #1e222b;
    color: #f3f4f6;
    border: 1px solid #2a2f3a;
    border-radius: 6px;
    padding: 4px 10px;
}
QPushButton:hover, QToolButton:hover {
    background-color: #2a2f3a;
}
QPushButton:checked, QToolButton:checked {
    background-color: #2563eb;
    border-color: #2563eb;
    color: #ffffff;
}
"""

MODERN_LIGHT_QSS = """
QMainWindow, QDialog {
    background-color: #f1f5f9;
    color: #0f172a;
}
QDockWidget {
    color: #0f172a;
    font-weight: 600;
}
QDockWidget::title {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 4px;
    padding: 6px 10px;
}
QToolBar#simplified_quick_bar {
    background-color: #ffffff;
    border-bottom: 1px solid #cbd5e1;
    padding: 6px 10px;
    spacing: 6px;
}
QListWidget, QTreeWidget, QTableWidget, QLineEdit, QTextEdit, QPlainTextEdit, QComboBox {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    selection-background-color: #1d4ed8;
    selection-color: #ffffff;
}
QPushButton, QToolButton {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 4px 10px;
}
QPushButton:hover, QToolButton:hover {
    background-color: #e2e8f0;
}
QPushButton:checked, QToolButton:checked {
    background-color: #1d4ed8;
    border-color: #1d4ed8;
    color: #ffffff;
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
            self.theme_btn.setText('Thème : Noir')
        else:
            from openlp.core.ui.style import set_default_lightmode
            set_default_lightmode(app)
            app.setStyleSheet(MODERN_LIGHT_QSS)
            self.theme_btn.setText('Thème : Blanc')


def attach_simplified_mode(main_window):
    """
    Attach the SimplifiedModeController to the main window if not already attached.
    """
    if not hasattr(main_window, 'simplified_mode_controller'):
        main_window.simplified_mode_controller = SimplifiedModeController(main_window)
    return main_window.simplified_mode_controller
