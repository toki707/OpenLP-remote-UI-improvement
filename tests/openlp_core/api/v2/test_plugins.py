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
from collections import namedtuple
from pathlib import Path
from unittest.mock import MagicMock

from PyQt5 import QtCore

from openlp.core.common.registry import Registry
from openlp.core.common.enum import PluginStatus
from openlp.core.display.render import Renderer
from openlp.core.lib.serviceitem import ServiceItem
from openlp.core.state import State
from openlp.core.api.versions.v2.plugins import search
from tests.openlp_core.lib.test_serviceitem import TEST_PATH as SERVICEITEM_TEST_PATH
from tests.utils import convert_file_service_item


def test_search_threaded(registry, settings):
    """Test that the search function calls the search method correctly when threaded"""
    # GIVEN: A mocked plugin, and plugin manager
    mocked_songs_plugin = MagicMock()
    mocked_songs_plugin.status = PluginStatus.Active
    mocked_songs_plugin.media_item.has_search = True
    mocked_songs_plugin.media_item.search.__pyqtSignature__ = 'slot'
    mocked_songs_plugin.media_item.staticMetaObject.invokeMethod.return_value = [[1, 'Test', 'This is a test']]
    mocked_plugin_manager = MagicMock(**{'get_plugin_by_name.return_value': mocked_songs_plugin})
    Registry().register('plugin_manager', mocked_plugin_manager)

    # WHEN: the search function is called
    result = search('songs', 'test')

    # THEN: A song should be returned via the invokeMethod method
    assert result == [[1, 'Test', 'This is a test']]
    mocked_songs_plugin.media_item.staticMetaObject.invokeMethod.assert_called_once()
    invoke_call = mocked_songs_plugin.media_item.staticMetaObject.invokeMethod.call_args_list[0]
    assert invoke_call.args[0] is mocked_songs_plugin.media_item
    assert invoke_call.args[1] == 'search'
    assert invoke_call.args[2] == QtCore.Qt.ConnectionType.DirectConnection


def test_search_unthreaded(registry, settings):
    """Test that the search function calls the search method correctly when we don't care about threads"""
    # GIVEN: A mocked plugin, and plugin manager
    mocked_songs_plugin = MagicMock()
    mocked_songs_plugin.status = PluginStatus.Active
    mocked_songs_plugin.media_item.has_search = True
    mocked_songs_plugin.media_item.search.return_value = [[1, 'Test', 'This is a test']]
    mocked_plugin_manager = MagicMock(**{'get_plugin_by_name.return_value': mocked_songs_plugin})
    Registry().register('plugin_manager', mocked_plugin_manager)

    # WHEN: the search function is called
    result = search('songs', 'test')

    # THEN: A song should be returned via the regular search method
    assert result == [[1, 'Test', 'This is a test']]
    mocked_songs_plugin.media_item.staticMetaObject.invokeMethod.assert_not_called()
    mocked_songs_plugin.media_item.search.assert_called_once_with('test', False)


def test_search_nothing(registry, settings):
    """Test that the search function returns None when there are no plugins by that name enabled"""
    # GIVEN: A mocked plugin, and plugin manager
    mocked_songs_plugin = MagicMock()
    mocked_songs_plugin.status = PluginStatus.Disabled
    mocked_plugin_manager = MagicMock(**{'get_plugin_by_name.return_value': mocked_songs_plugin})
    Registry().register('plugin_manager', mocked_plugin_manager)

    # WHEN: the search function is called
    result = search('songs', 'test')

    # THEN: None should be returned
    assert result is None


def test_bibles_search_options_returns_list(flask_client, settings):
    """
    Test a list is returned when a plugin's search options are requested.

    Returns an empty list here because the plugin is mocked so there are no options.
    """
    # GIVEN: A mocked plugin
    mock_plugin_manager = MagicMock()
    mock_plugin_manager.get_plugin_by_name.return_value = MagicMock()
    Registry().register('plugin_manager', mock_plugin_manager)

    # WHEN: Search options are requested
    res = flask_client.get('/api/v2/plugins/bibles/search-options').get_json()

    # THEN: A empty list should be returned
    assert res == []


def test_bibles_set_search_options_sets_bible_version(flask_client, settings):
    """
    Test that a search option post request sends the correct values to the plugin,
    and returns the correct status code.
    """
    # GIVEN: A mocked bible plugin
    mock_plugin_manager = MagicMock()
    mock_bible_plugin = MagicMock()
    mock_bible_plugin.status = PluginStatus.Active
    mock_bible_plugin.media_item = MagicMock(set_search_option=MagicMock(return_value=True))
    mock_plugin_manager.get_plugin_by_name.return_value = mock_bible_plugin
    Registry().register('plugin_manager', mock_plugin_manager)

    # WHEN: The primary bible is requested to change via the api
    res = flask_client.post('/api/v2/plugins/bibles/search-options', json=dict(option='primary bible', value='foo'))

    # THEN: Returns correct status code and sends correct values to plugin.
    assert res.status_code == 204
    mock_bible_plugin.media_item.set_search_option.assert_called_once_with('primary bible', 'foo')


def test_plugin_set_search_option_aborts_if_no_option(flask_client, settings):
    Registry().register('plugin_manager', MagicMock())
    res = flask_client.post('/api/v2/plugins/songs/search-options', json={})
    assert res.status_code == 400


def test_plugin_set_search_option_aborts_if_invalid_option(flask_client, settings):
    Registry().register('plugin_manager', MagicMock())
    res1 = flask_client.post('/api/v2/plugins/songs/search-options', json=dict(option=['']))
    res2 = flask_client.post('/api/v2/plugins/songs/search-options', json=dict(option={1: '', 2: ''}))
    assert res1.status_code == 400
    assert res2.status_code == 400


def test_plugin_search_options_returns_no_search_options(flask_client, settings):
    Registry().register('plugin_manager', MagicMock())
    res = flask_client.get('/api/v2/plugins/songs/search-options')
    assert res.status_code == 200


def test_plugin_set_search_option_returns_plugin_exception(flask_client, settings):
    Registry().register('plugin_manager', MagicMock())
    res = flask_client.post('/api/v2/plugins/songs/search-options', json=dict(option=''))
    assert res.status_code == 400


def test_plugin_songs_transpose_returns_plugin_exception(flask_client, settings):
    Registry().register('plugin_manager', MagicMock())
    res = flask_client.get('/api/v2/plugins/songs/transpose-live-item/test')
    assert res.status_code == 400


TransposeMockReturn = namedtuple('TransposeMockReturn', ['renderer_mock_any_attr', 'live_controller_mock'])


def _init_transpose_mocks():
    # GIVEN: A mocked plugin_manager, live_controller, renderer and a real service item with the internal slide cache
    # filled
    Registry().register('plugin_manager', MagicMock())
    renderer_mock = MagicMock()
    # Mocking every Renderer attribute with a shared mock so we can know whether any property of it was called
    renderer_mock_any_attr = MagicMock(name='Renderer attribute/call')
    for name in dir(Renderer):
        # Mocking every Renderer property
        # skipping dunder/hide methods
        if not name.startswith('_'):
            setattr(renderer_mock, name, renderer_mock_any_attr)
    # Mocking format_slides to return the correct data to ServiceItem
    renderer_mock.format_slide.side_effect = lambda text, item: text
    Registry().register('renderer', renderer_mock)
    service_item = ServiceItem()
    live_controller_mock = MagicMock()
    live_controller_mock.service_item = service_item
    Registry().register('live_controller', live_controller_mock)
    # Using a real item to test this
    line = convert_file_service_item(SERVICEITEM_TEST_PATH, 'serviceitem-song-linked-audio.osj')
    State().load_settings()  # needed to make the below method not fail
    service_item.set_from_service(line, Path('/test/'))
    # Trying to retrive the slides to trigger the cache prime process (as it's primed when using the service item first
    # time in OpenLP)
    service_item.rendered_slides
    # Resetting the mocks to correctly compute illegal calls
    renderer_mock_any_attr.reset_mock()
    renderer_mock.format_slides.reset_mock()

    return TransposeMockReturn(renderer_mock_any_attr=renderer_mock_any_attr,
                               live_controller_mock=live_controller_mock)


def test_plugin_songs_transpose_wont_call_renderer(flask_client, settings):
    """
    Tests whether the transpose endpoint won't tries to use any Renderer method; the endpoint needs to operate using
    already-primed caches (as that's what the /live-item endpoint does); also using Renderer from outside the Qt loop
    causes it to crash.

    See https://gitlab.com/openlp/openlp/-/merge_requests/516 for some background on this.
    """
    # GIVEN: The default mocks for Transpose API
    mocks = _init_transpose_mocks()

    # WHEN: The endpoint is called
    flask_client.get('/api/v2/plugins/songs/transpose-live-item/-1')

    # THEN: The renderer should not be called
    mocks.renderer_mock_any_attr.assert_not_called()


def test_plugin_songs_transpose_accepts_response_format_service_item(flask_client, settings):
    """
    Tests whether the transpose's return_service_item parameter works
    """

    # GIVEN: The default mocks for Transpose API and the default response
    _init_transpose_mocks()

    # WHEN: The transpose action returning service_item is called
    service_item_res = flask_client.get('/api/v2/plugins/songs/transpose-live-item/-1?response_format=service_item')

    # THEN: The service item response shouldn't match normal response and should be a service_item response
    response = service_item_res.json
    assert 'capabilities' in response


def test_plugin_songs_transpose_marks_selected_slide(flask_client, settings):
    """
    Tests whether the transpose's endpoint marks the active slide
    """

    # GIVEN: The default mocks for Transpose API and the default response
    mocks = _init_transpose_mocks()
    mocks.live_controller_mock.selected_row = 1

    # WHEN: The transpose action returning service_item is called
    service_item_res = flask_client.get('/api/v2/plugins/songs/transpose-live-item/-1?response_format=service_item')

    # THEN: The service item response shouldn't match normal response and should be a service_item response
    response = service_item_res.json
    assert response['slides'][1]['selected'] is True


def test_plugin_preview_endpoint(flask_client, settings):
    """Test that /api/v2/plugins/<plugin>/preview builds a service item and sends it to preview_controller"""
    fake_preview_controller = MagicMock()
    fake_service_item = MagicMock()
    mock_plugin = MagicMock()
    mock_plugin.status = PluginStatus.Active
    mock_plugin.media_item.create_item_from_id.return_value = 'item-obj'
    mock_plugin.media_item.build_service_item.return_value = fake_service_item
    mock_plugin_manager = MagicMock(**{'get_plugin_by_name.return_value': mock_plugin})
    Registry().register('plugin_manager', mock_plugin_manager)
    Registry().register('preview_controller', fake_preview_controller)

    res = flask_client.post('/api/v2/plugins/bibles/preview', json={'id': 'Jean 3:16'})
    assert res.status_code == 204
    fake_preview_controller.add_service_item.assert_called_once_with(fake_service_item)
    assert fake_service_item.from_plugin is True

    res_bad = flask_client.post('/api/v2/plugins/bibles/preview', json={})
    assert res_bad.status_code == 400


def test_list_images_endpoint(flask_client, settings, tmp_path):
    """Test that /api/v2/plugins/images/list returns image metadata and thumbnails"""
    from unittest.mock import patch
    img_file = tmp_path / 'affiche.png'
    img_file.write_bytes(b'png-bytes')
    thumb_file = tmp_path / 'affiche_thumb.png'
    thumb_file.write_bytes(b'thumb-bytes')

    fake_db_item = MagicMock()
    fake_db_item.id = 1
    fake_db_item.file_path = str(img_file)

    mock_plugin = MagicMock()
    mock_plugin.status = PluginStatus.Active
    mock_plugin.media_item.manager.get_all_objects.return_value = [fake_db_item]
    mock_plugin.media_item.generate_thumbnail_path.return_value = thumb_file
    mock_plugin_manager = MagicMock(**{'get_plugin_by_name.return_value': mock_plugin})
    Registry().register('plugin_manager', mock_plugin_manager)

    with patch('openlp.core.api.versions.v2.plugins.image_to_data_uri', return_value='data:image/png;base64,123'):
        res = flask_client.get('/api/v2/plugins/images/list')
        assert res.status_code == 200
        data = res.get_json()
        assert len(data) == 1
        assert data[0]['filename'] == 'affiche.png'
        assert data[0]['thumbnail'] == 'data:image/png;base64,123'


def test_upload_image_endpoint(flask_client, settings, tmp_path):
    """Test uploading a base64 image from mobile gallery and triggering preview/live/service"""
    from unittest.mock import patch
    thumb_file = tmp_path / 'uploaded_thumb.png'
    thumb_file.write_bytes(b'thumb')

    fake_preview_controller = MagicMock()
    mock_plugin = MagicMock()
    mock_plugin.status = PluginStatus.Active
    mock_plugin.media_item.manager.get_object_filtered.return_value = None
    mock_plugin.media_item.generate_thumbnail_path.return_value = thumb_file
    mock_plugin.media_item.build_service_item.return_value = MagicMock()
    mock_plugin_manager = MagicMock(**{'get_plugin_by_name.return_value': mock_plugin})
    Registry().register('plugin_manager', mock_plugin_manager)
    Registry().register('preview_controller', fake_preview_controller)

    tiny_b64 = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=='
    with patch('openlp.core.api.versions.v2.plugins.AppLocation.get_section_data_path', return_value=tmp_path), \
         patch('openlp.core.api.versions.v2.plugins.create_thumb'), \
         patch('openlp.core.api.versions.v2.plugins.image_to_data_uri', return_value='data:image/png;base64,THUMB'):
        for act in ('preview', 'live', 'service'):
            res = flask_client.post('/api/v2/plugins/images/upload', json={
                'filename': f'gallery_{act}.png',
                'data': tiny_b64,
                'action': act
            })
            assert res.status_code == 201
            body = res.get_json()
            assert body['thumbnail'] == 'data:image/png;base64,THUMB'
        assert fake_preview_controller.add_service_item.called
        assert mock_plugin.media_item.go_live.called
        assert mock_plugin.media_item.add_to_service.called


def test_custom_list_and_save_endpoints(flask_client, settings):
    """Test listing and creating/updating custom slides via /api/v2/plugins/custom/list and /save"""
    from openlp.plugins.custom.lib.customxmlhandler import CustomXML
    cxml = CustomXML()
    cxml.add_verse_to_lyrics('custom', '1', 'MARCHER PAR LA FOI')
    xml_text = str(cxml.extract_xml(), 'utf-8')

    fake_slide = MagicMock()
    fake_slide.id = 10
    fake_slide.title = 'Thème de la Parole'
    fake_slide.text = xml_text
    fake_slide.credits = '2 Corinthiens 5:7'
    fake_slide.theme_name = 'Parole Biblique'

    fake_preview_controller = MagicMock()
    mock_plugin = MagicMock()
    mock_plugin.status = PluginStatus.Active
    mock_plugin.db_manager.get_all_objects.return_value = [fake_slide]
    mock_plugin.db_manager.get_object.return_value = fake_slide
    mock_plugin.media_item.build_service_item.return_value = MagicMock()
    mock_plugin_manager = MagicMock(**{'get_plugin_by_name.return_value': mock_plugin})
    Registry().register('plugin_manager', mock_plugin_manager)
    Registry().register('preview_controller', fake_preview_controller)

    res_list = flask_client.get('/api/v2/plugins/custom/list')
    assert res_list.status_code == 200
    items = res_list.get_json()
    assert len(items) == 1
    assert items[0]['title'] == 'Thème de la Parole'
    assert items[0]['slides'] == ['MARCHER PAR LA FOI']

    for act in ('preview', 'live', 'service'):
        res_save = flask_client.post('/api/v2/plugins/custom/save', json={
            'id': 10 if act == 'preview' else None,
            'title': 'Nouveau Thème',
            'text': 'Diapo 1\n---\nDiapo 2',
            'credits': 'Pasteur',
            'theme_name': 'Message du Jour',
            'action': act
        })
        assert res_save.status_code == 200
        saved = res_save.get_json()
        assert saved['title'] == 'Nouveau Thème'
        assert len(saved['slides']) == 2


def test_list_bible_books_endpoint(flask_client, settings):
    """Test /api/v2/plugins/bibles/books returns books and chapter counts"""
    fake_book = MagicMock()
    fake_book.get_name.return_value = 'Jean'
    fake_book.abbreviation = 'Jn'

    mock_plugin = MagicMock()
    mock_plugin.status = PluginStatus.Active
    mock_plugin.manager.get_bibles.return_value = {'Louis Segond': MagicMock()}
    mock_plugin.media_item.bible.name = 'Louis Segond'
    mock_plugin.media_item.bible.get_books.return_value = [fake_book]
    mock_plugin.manager.get_chapter_count.return_value = 21
    mock_plugin_manager = MagicMock(**{'get_plugin_by_name.return_value': mock_plugin})
    Registry().register('plugin_manager', mock_plugin_manager)

    res = flask_client.get('/api/v2/plugins/bibles/books')
    assert res.status_code == 200
    data = res.get_json()
    assert data['primary_bible'] == 'Louis Segond'
    assert data['books'][0]['name'] == 'Jean'
    assert data['books'][0]['chapters'] == 21


def test_mobile_endpoints_inactive_plugins_and_error_branches(flask_client, settings):
    """Test error branches and inactive plugin responses for new mobile endpoints"""
    inactive_plugin = MagicMock()
    inactive_plugin.status = PluginStatus.Disabled
    mock_plugin_manager = MagicMock(**{'get_plugin_by_name.return_value': inactive_plugin})
    Registry().register('plugin_manager', mock_plugin_manager)

    assert flask_client.get('/api/v2/plugins/images/list').get_json() == []
    assert flask_client.get('/api/v2/plugins/custom/list').get_json() == []
    assert flask_client.get('/api/v2/plugins/bibles/books').get_json() == {
        'primary_bible': '', 'bibles': [], 'books': []
    }
    assert flask_client.post('/api/v2/plugins/images/upload', json={}).status_code == 400
    assert flask_client.post('/api/v2/plugins/custom/save', json={}).status_code == 400


