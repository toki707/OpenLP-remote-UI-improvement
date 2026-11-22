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
import logging

from pathlib import Path
from openlp.core.api.lib import login_required, call_on_main_thread
from openlp.core.common import ThemeLevel
from openlp.core.common.json import OpenLPJSONEncoder
from openlp.core.common.registry import Registry
from openlp.core.lib import image_to_data_uri, create_thumb

import json
from flask import jsonify, request, abort, Blueprint, Response

controller_views = Blueprint('controller', __name__)
log = logging.getLogger(__name__)


@controller_views.route('/live-items')
def controller_live_items():
    log.debug('controller-v2-live-items')
    live_controller = Registry().get('live_controller')
    current_item = live_controller.service_item
    live_item = {}
    if current_item:
        live_item = current_item.to_dict()
        live_item['slides'][live_controller.selected_row]['selected'] = True
        live_item['id'] = str(current_item.unique_identifier)
        _enrich_image_slides(current_item, live_item)
    json_live_item = json.dumps(live_item, cls=OpenLPJSONEncoder)
    return Response(json_live_item, mimetype='application/json')


@controller_views.route('/live-item')
def controller_live_item():
    log.debug('controller-v2-live-item')
    live_controller = Registry().get('live_controller')
    current_item = live_controller.service_item
    live_item = {}
    if current_item:
        live_item = current_item.to_dict(True, live_controller.selected_row)
        live_item['id'] = str(current_item.unique_identifier)
    json_live_item = json.dumps(live_item, cls=OpenLPJSONEncoder)
    return Response(json_live_item, mimetype='application/json')


@controller_views.route('/show', methods=['POST'])
@login_required
def controller_set():
    log.debug('controller-v2-show-post')
    data = request.json
    if not data:
        log.error('Missing request data')
        abort(400)
    num = data.get('id', -1)
    Registry().get('live_controller').slidecontroller_live_set.emit([num])
    return '', 204


@controller_views.route('/progress', methods=['POST'])
@login_required
def controller_direction():
    log.debug('controller-v2-progress-post')
    ALLOWED_ACTIONS = ['next', 'previous']
    data = request.json
    if not data:
        log.error('Missing request data')
        abort(400)
    action = data.get('action', '').lower()
    if action not in ALLOWED_ACTIONS:
        log.error('Invalid action passed ' + action)
        abort(400)
    getattr(Registry().get('live_controller'), 'slidecontroller_live_{action}'.
            format(action=action)).emit()
    return '', 204


@controller_views.route('/theme-level', methods=['GET'])
@login_required
def get_theme_level():
    log.debug('controller-v2-theme-level-get')
    theme_level = Registry().get('settings').value('themes/theme level')
    if theme_level == ThemeLevel.Global:
        theme_level = 'global'
    elif theme_level == ThemeLevel.Service:
        theme_level = 'service'
    elif theme_level == ThemeLevel.Song:
        theme_level = 'song'
    return jsonify(theme_level)


@controller_views.route('/theme-level', methods=['POST'])
@login_required
def set_theme_level():
    log.debug('controller-v2-theme-level-post')
    data = request.json
    if not data:
        log.error('Missing request data')
        abort(400)
    theme_level = ''
    try:
        theme_level = str(data.get("level"))
    except ValueError:
        log.error('Invalid data passed ' + theme_level)
        abort(400)
    if theme_level == 'global':
        Registry().get('settings').setValue('themes/theme level', 1)
    elif theme_level == 'service':
        Registry().get('settings').setValue('themes/theme level', 2)
    elif theme_level == 'song':
        Registry().get('settings').setValue('themes/theme level', 3)
    else:
        log.error('Unsupported data passed ' + theme_level)
        abort(400)
    Registry().get('theme_manager').theme_level_updated.emit()
    return '', 204


@controller_views.route('/themes', methods=['GET'])
def get_themes():
    """
    Gets a list of all existing themes
    """
    log.debug('controller-v2-themes-get')
    theme_level = Registry().get('settings').value('themes/theme level')
    theme_list = []
    current_theme = ''
    if theme_level == ThemeLevel.Global:
        current_theme = Registry().get('theme_manager').global_theme
    if theme_level == ThemeLevel.Service:
        current_theme = Registry().get('service_manager').service_theme
    # Gets and appends theme list
    themes = Registry().execute('get_theme_names')
    try:
        for theme in themes[0]:
            # Gets the background path, get the thumbnail from it, and encode it to a base64 data uri
            theme_path = Registry().get('theme_manager').theme_path
            encoded_thumb = image_to_data_uri(theme_path / 'thumbnails' / '{file_name}.png'.format(file_name=theme))
            # Append the theme to the list
            theme_list.append({
                'name': theme,
                'selected': False,
                'thumbnail': encoded_thumb
            })
        for i in theme_list:
            if i["name"] == current_theme:
                i["selected"] = True
    except IndexError:
        log.error('Missing theme passed ' + str(themes))
        pass
    return jsonify(theme_list)


@controller_views.route('/themes/<theme_name>', methods=['GET'])
def get_theme_data(theme_name):
    """
    Get a theme's data
    """
    log.debug(f'controller-v2-theme-data-get {theme_name}')
    themes = Registry().execute('get_theme_names')[0]
    if theme_name not in themes:
        log.error('Requested non-existent theme')
        abort(404)
    theme_data = Registry().get('theme_manager').get_theme_data(theme_name).export_theme_self_contained(True)
    return Response(theme_data, mimetype='application/json')


@controller_views.route('/live-theme', methods=['GET'])
def get_live_theme_data():
    """
    Get the live theme's data
    """
    log.debug('controller-v2-live-theme-data-get')
    live_service_item = Registry().get('live_controller').service_item
    if live_service_item:
        theme_data = live_service_item.get_theme_data()
    else:
        theme_data = Registry().get('theme_manager').get_theme_data(None)
    self_contained_theme = theme_data.export_theme_self_contained(True)
    return Response(self_contained_theme, mimetype='application/json')


@controller_views.route('/theme', methods=['GET'])
def get_theme():
    """
    Get the current theme name
    """
    log.debug('controller-v2-theme-get')
    theme_level = Registry().get('settings').value('themes/theme level')
    if theme_level == ThemeLevel.Service:
        theme = Registry().get('settings').value('servicemanager/service theme')
    else:
        theme = Registry().get('settings').value('themes/global theme')
    return jsonify(theme)


@controller_views.route('/theme', methods=['POST'])
@login_required
def set_theme():
    log.debug('controller-v2-themes-post')
    data = request.json
    theme = ''
    theme_level = Registry().get('settings').value('themes/theme level')
    if not data:
        log.error('Missing request data')
        abort(400)
    try:
        theme = str(data.get('theme'))
    except ValueError:
        log.error('Invalid data passed ' + theme)
        abort(400)
    if theme_level == ThemeLevel.Global:
        Registry().get('settings').setValue('themes/global theme', theme)
        Registry().get('theme_manager').theme_update_global.emit()
    elif theme_level == ThemeLevel.Service:
        Registry().get('settings').setValue('servicemanager/service theme', theme)
        Registry().get('service_manager').theme_update_service.emit()
    elif theme_level == ThemeLevel.Song:
        log.error('Unimplemented method')
        return '', 501
    return '', 204


@controller_views.route('/clear/<controller>', methods=['POST'])
@login_required
def controller_clear(controller):
    """
    Clears the slide controller display
    :param controller: the Live or Preview controller
    :return: HTTP return code
    """
    log.debug(f'controller-v2-clear-get {controller}')
    if controller in ['live', 'preview']:
        getattr(Registry().get(f'{controller}_controller'), f'slidecontroller_{controller}_clear').emit()
        return '', 204
    else:
        return '', 404


def _enrich_image_slides(service_item, item_dict):
    """
    Ensure image slides always include a base64 ``img`` preview data URI for the mobile remote.
    """
    if not service_item or not hasattr(service_item, 'is_image') or service_item.is_image() is not True:
        return item_dict
    frames = service_item.get_frames()
    slides = item_dict.get('slides', [])
    for idx, slide in enumerate(slides):
        if not slide.get('img') and idx < len(frames):
            frame = frames[idx]
            thumb = frame.get('thumbnail')
            if thumb:
                thumb_path = Path(thumb)
                if not thumb_path.exists():
                    create_thumb(Path(service_item.get_frame_path(idx)), thumb_path, False)
                if thumb_path.exists():
                    slide['img'] = image_to_data_uri(thumb_path)
            if not slide.get('img') and frame.get('path'):
                src_path = Path(frame['path'])
                if src_path.exists():
                    slide['img'] = image_to_data_uri(src_path)
    return item_dict


@controller_views.route('/preview-items')
def controller_preview_items():
    """
    Return the current service item and slides loaded in the Preview controller.
    """
    log.debug('controller-v2-preview-items')
    preview_controller = Registry().get('preview_controller')
    current_item = preview_controller.service_item if preview_controller else None
    preview_item = {}
    if current_item:
        preview_item = current_item.to_dict()
        selected_row = preview_controller.selected_row or 0
        if preview_item.get('slides') and 0 <= selected_row < len(preview_item['slides']):
            preview_item['slides'][selected_row]['selected'] = True
        preview_item['id'] = str(current_item.unique_identifier)
        _enrich_image_slides(current_item, preview_item)
    json_preview_item = json.dumps(preview_item, cls=OpenLPJSONEncoder)
    return Response(json_preview_item, mimetype='application/json')


@controller_views.route('/preview/show', methods=['POST'])
@login_required
def controller_preview_set():
    """
    Select a specific slide index in the Preview controller.
    """
    log.debug('controller-v2-preview-show-post')
    data = request.json
    if not data:
        abort(400)
    num = data.get('id', -1)
    Registry().get('preview_controller').slidecontroller_preview_set.emit([num])
    return '', 204


@controller_views.route('/preview/progress', methods=['POST'])
@login_required
def controller_preview_direction():
    """
    Move to next or previous slide in the Preview controller.
    """
    log.debug('controller-v2-preview-progress-post')
    allowed_actions = ['next', 'previous']
    data = request.json
    if not data:
        abort(400)
    action = data.get('action', '').lower()
    if action not in allowed_actions:
        abort(400)
    getattr(Registry().get('preview_controller'), f'slidecontroller_preview_{action}').emit()
    return '', 204


@controller_views.route('/preview/go-live', methods=['POST'])
@login_required
def controller_preview_go_live():
    """
    Send the item currently in the Preview controller to the Live controller.
    """
    log.debug('controller-v2-preview-go-live-post')
    preview_controller = Registry().get('preview_controller')
    if not preview_controller or not preview_controller.service_item:
        abort(400)
    call_on_main_thread(preview_controller.on_go_live)
    return '', 204

