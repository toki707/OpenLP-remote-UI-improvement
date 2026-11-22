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
Unit tests for the Simplified Youth/Church Mode & Live Dark/Light Theme Switcher.
"""
from unittest.mock import MagicMock, patch
from PyQt5 import QtWidgets

from openlp.core.lib.plugin import PluginStatus
from openlp.core.ui.simplifiedmode import SimplifiedModeController, attach_simplified_mode


def test_attach_simplified_mode_and_focus_tab(qapp):
    """
    Test attaching SimplifiedModeController to a MainWindow and switching library tabs.
    """
    main_win = QtWidgets.QMainWindow()
    main_win.media_manager_dock = MagicMock()
    main_win.media_manager_dock.isVisible.return_value = False
    main_win.projector_manager_dock = MagicMock()
    main_win.media_dock_manager = MagicMock()

    bible_widget = QtWidgets.QWidget()
    bible_widget.settings_section = 'bibles'
    images_widget = QtWidgets.QWidget()
    images_widget.settings_section = 'images'

    toolbox = QtWidgets.QToolBox()
    toolbox.addItem(bible_widget, 'Bibles')
    toolbox.addItem(images_widget, 'Images')
    main_win.media_tool_box = toolbox

    ctrl = attach_simplified_mode(main_win)
    assert isinstance(ctrl, SimplifiedModeController)
    assert attach_simplified_mode(main_win) is ctrl

    ctrl.focus_plugin_tab('images')
    main_win.media_manager_dock.setVisible.assert_called_with(True)
    assert toolbox.currentIndex() == 1
    assert ctrl.quick_buttons['images'].isChecked() is True
    assert ctrl.quick_buttons['bibles'].isChecked() is False


def test_toggle_simple_mode_filters_plugins(qapp):
    """
    Test toggling Simplified Mode removes non-youth plugins and restores them when turned off.
    """
    main_win = QtWidgets.QMainWindow()
    main_win.media_manager_dock = MagicMock()
    main_win.media_manager_dock.isVisible.return_value = True
    main_win.projector_manager_dock = MagicMock()
    main_win.media_dock_manager = MagicMock()
    main_win.media_tool_box = QtWidgets.QToolBox()

    bibles_plugin = MagicMock()
    bibles_plugin.name = 'bibles'
    bibles_plugin.status = PluginStatus.Active
    bibles_plugin.media_item = MagicMock()

    presentations_plugin = MagicMock()
    presentations_plugin.name = 'presentations'
    presentations_plugin.status = PluginStatus.Active
    presentations_plugin.media_item = MagicMock()

    ctrl = attach_simplified_mode(main_win)
    with patch('openlp.core.ui.simplifiedmode.State.list_plugins',
               return_value=[bibles_plugin, presentations_plugin]):
        ctrl.simple_mode_btn.setChecked(True)
        ctrl.toggle_simple_mode()
        assert ctrl.is_simple_mode is True
        main_win.projector_manager_dock.setVisible.assert_called_once_with(False)
        main_win.media_dock_manager.remove_dock.assert_called_once_with(presentations_plugin.media_item)

        ctrl.simple_mode_btn.setChecked(False)
        ctrl.toggle_simple_mode()
        assert ctrl.is_simple_mode is False
        assert main_win.media_dock_manager.add_item_to_dock.call_count == 2


def test_toggle_color_theme(qapp):
    """
    Test toggling between Dark and Light themes updates application palette and button label.
    """
    main_win = QtWidgets.QMainWindow()
    main_win.media_manager_dock = MagicMock()
    main_win.media_tool_box = QtWidgets.QToolBox()
    ctrl = attach_simplified_mode(main_win)

    with patch('openlp.core.ui.style.set_default_lightmode') as mock_light, \
         patch('openlp.core.ui.style.set_default_darkmode') as mock_dark:
        ctrl.toggle_color_theme()
        assert ctrl.is_dark_theme is False
        assert mock_light.called
        assert 'Blanc' in ctrl.theme_btn.text()

        ctrl.toggle_color_theme()
        assert ctrl.is_dark_theme is True
        assert mock_dark.called
        assert 'Noir' in ctrl.theme_btn.text()
