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

from unittest.mock import patch
from openlp.core.api import app as flask_app
from openlp.core.api.lib import MainThreadDispatcher, call_on_main_thread
from openlp.core.api.main import _get_remotes_dir, get_mime_type


def test_get_mime_type():
    assert get_mime_type('index.html') == 'text/html'
    assert get_mime_type('stage.js') == 'application/javascript'
    assert get_mime_type('stage.css') == 'text/css'


def test_get_remotes_dir_falls_back_to_bundled(tmp_path):
    with patch('openlp.core.api.main.AppLocation.get_section_data_path', return_value=tmp_path):
        remotes_dir = _get_remotes_dir()
        assert (remotes_dir / 'index.html').exists()


def test_main_index_and_assets_routes(tmp_path):
    flask_app.config['TESTING'] = True
    client = flask_app.test_client()
    with patch('openlp.core.api.main.AppLocation.get_section_data_path', return_value=tmp_path):
        res_index = client.get('/')
        assert res_index.status_code == 200
        assert b'OpenLP Remote' in res_index.data
        assert b'data-theme="light"' in res_index.data
        assert b'ios-navbar' in res_index.data
        assert b'ios-seg' in res_index.data
        assert b'ios-dock' in res_index.data
        assert b'mac-sidebar' in res_index.data
        assert b'mac-toolbar' in res_index.data

        res_asset = client.get('/assets/version.js')
        assert res_asset.status_code == 200
        assert b'appVersion' in res_asset.data


def test_call_on_main_thread_and_dispatcher():
    assert call_on_main_thread(lambda: 42) == 42
    dispatcher = MainThreadDispatcher()
    box = {'value': None, 'error': None}
    dispatcher._on_execute((lambda: 'ok', None, box))
    assert box['value'] == 'ok'
    assert box['error'] is None

