# -*- coding: utf-8 -*-
# vim: autoindent shiftwidth=4 expandtab textwidth=120 tabstop=4 softtabstop=4

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
import base64
import logging
import json
import re
import time
from pathlib import Path

from flask import abort, request, Blueprint, jsonify, Response
from PyQt5 import QtCore

from openlp.core.api.lib import login_required, extract_request, old_success_response, old_auth, call_on_main_thread
from openlp.core.common import sha256_file_hash
from openlp.core.common.applocation import AppLocation
from openlp.core.common.path import create_paths
from openlp.core.lib import ServiceItemContext, image_to_data_uri, create_thumb
from openlp.core.lib.plugin import PluginStatus
from openlp.core.common.json import OpenLPJSONEncoder
from openlp.core.common.registry import Registry
from openlp.plugins.songs.lib import transpose_lyrics

log = logging.getLogger(__name__)


plugins = Blueprint('v2-plugins', __name__)
alert_1_views = Blueprint('v1-alert-plugin', __name__)
alert_2_views = Blueprint('v2-alert-plugin', __name__)


def search(plugin_name, text):
    plugin = Registry().get('plugin_manager').get_plugin_by_name(plugin_name)
    if plugin.status == PluginStatus.Active and plugin.media_item and plugin.media_item.has_search:
        if hasattr(plugin.media_item.search, '__pyqtSignature__'):
            # If this method has a signature, it means that it should be called from the parent thread
            results = plugin.media_item.staticMetaObject.invokeMethod(
                plugin.media_item, 'search', QtCore.Qt.ConnectionType.DirectConnection,
                QtCore.Q_RETURN_ARG(list), QtCore.Q_ARG(str, text), QtCore.Q_ARG(bool, False))
        else:
            # Fall back to original behaviour
            results = plugin.media_item.search(text, False)
        return results
    return None


def live(plugin_name, id):
    plugin = Registry().get('plugin_manager').get_plugin_by_name(plugin_name)
    if plugin.status == PluginStatus.Active and plugin.media_item:
        getattr(plugin.media_item, '{action}_go_live'.format(action=plugin_name)).emit([id, True])


def add(plugin_name, id):
    plugin = Registry().get('plugin_manager').get_plugin_by_name(plugin_name)
    if plugin.status == PluginStatus.Active and plugin.media_item:
        item_id = plugin.media_item.create_item_from_id(id)
        getattr(plugin.media_item, '{action}_add_to_service'.format(action=plugin_name)).emit([item_id, True])


def preview(plugin_name, id):
    plugin = Registry().get('plugin_manager').get_plugin_by_name(plugin_name)
    if plugin and plugin.status == PluginStatus.Active and plugin.media_item:
        def _do_preview():
            item = plugin.media_item.create_item_from_id(id)
            service_item = plugin.media_item.build_service_item(
                item, remote=True, context=ServiceItemContext.Preview)
            if service_item:
                service_item.from_plugin = True
                Registry().get('preview_controller').add_service_item(service_item)
        call_on_main_thread(_do_preview)


def get_options(plugin_name):
    plugin = Registry().get('plugin_manager').get_plugin_by_name(plugin_name)
    if plugin.status == PluginStatus.Active and plugin.media_item:
        options = plugin.media_item.search_options()
        return options
    return []


def set_option(plugin_name, search_option, value):
    plugin = Registry().get('plugin_manager').get_plugin_by_name(plugin_name)
    success = False
    if plugin.status == PluginStatus.Active and plugin.media_item:
        success = plugin.media_item.set_search_option(search_option, value)
    return success


@plugins.route('/<plugin>/search')
@login_required
def search_view(plugin):
    log.debug(f'{plugin}/search called')
    text = request.args.get('text', '')
    result = search(plugin, text)
    return jsonify(result)


@plugins.route('/<plugin>/add', methods=['POST'])
@login_required
def add_view(plugin):
    log.debug(f'{plugin}/add called')
    data = request.json
    if not data:
        abort(400)
    id = data.get('id', -1)
    add(plugin, id)
    return '', 204


@plugins.route('/<plugin>/live', methods=['POST'])
@login_required
def live_view(plugin):
    log.debug(f'{plugin}/live called')
    data = request.json
    if not data:
        abort(400)
    id = data.get('id', -1)
    live(plugin, id)
    return '', 204


@plugins.route('/<plugin>/preview', methods=['POST'])
@login_required
def preview_view(plugin):
    log.debug(f'{plugin}/preview called')
    data = request.json
    if not data:
        abort(400)
    id = data.get('id', -1)
    preview(plugin, id)
    return '', 204


@plugins.route('/<plugin>/search-options', methods=['GET'])
def search_options(plugin):
    """
    Get the plugin's search options
    """
    log.debug(f'{plugin}/search-options called')
    return jsonify(get_options(plugin))


@plugins.route('/<plugin>/search-options', methods=['POST'])
@login_required
def set_search_option(plugin):
    """
    Sets the plugin's search options
    """
    log.debug(f'{plugin}/search-options-set called')
    data = request.json
    if not data:
        log.error('Missing request data')
        abort(400)
    option = data.get('option', None)
    value = data.get('value', None)
    if value is None:
        log.error('Invalid data passed in value')
        abort(400)

    if set_option(plugin, option, value):
        return '', 204
    else:
        log.error('Invalid option or value')
        return '', 400


@plugins.route('/songs/transpose-live-item/<transpose_value>', methods=['GET'])
def transpose(transpose_value):
    log.debug('songs/transpose-live-item called')
    response_format = request.args.get('response_format', None, type=str)
    return_service_item = response_format == 'service_item'
    if transpose_value:
        try:
            transpose_value = int(transpose_value)
        except ValueError:
            abort(400)
        # Get lyrics from the live serviceitem in the live-controller and transpose it
        live_controller = Registry().get('live_controller')
        current_item = live_controller.service_item
        # make sure an service item is currently displayed and that it is a song
        if not current_item or current_item.name != 'songs':
            abort(400)
        live_item = current_item.to_dict()
        live_item['id'] = str(current_item.unique_identifier)
        chord_song_text = ''
        verse_index = 1
        for item in live_item['slides']:
            chord_song_text += ('---[Verse:%d]---' % verse_index) + '\n'
            chord_song_text += item['chords'] + '\n'
            verse_index += 1
        # transpose
        transposed_lyrics = transpose_lyrics(chord_song_text, transpose_value)
        # re-split into verses
        chord_slides = []
        verse_list = re.split(r'---\[Verse:(.+?)\]---', transposed_lyrics)
        # remove first blank entry
        verse_list = verse_list[1:]
        j = 0
        for i in range(0, len(verse_list), 2):
            if return_service_item:
                live_item['slides'][j]['chords'] = verse_list[i + 1].strip()
                j += 1
            else:
                chord_slides.append({'chords': verse_list[i + 1].strip(), 'verse': verse_list[i]})
        if return_service_item:
            live_item['chords_transposed'] = True
            live_item['slides'][live_controller.selected_row]['selected'] = True
            json_live_item = json.dumps(live_item, cls=OpenLPJSONEncoder)
            return Response(json_live_item, mimetype='application/json')
        else:
            return jsonify(chord_slides), 200
    abort(400)


@alert_2_views.route('', methods=['POST'])
@login_required
def alert():
    data = request.json
    if not data:
        abort(400)
    alert = data.get('text', '')
    if alert:
        if Registry().get('plugin_manager').get_plugin_by_name('alerts').status == PluginStatus.Active:
            Registry().get('alerts_manager').alerts_text.emit([alert])
            return '', 204
    abort(400)


@alert_1_views.route('')
@old_auth
def old_alert():
    alert = extract_request(request.args.get('data', ''), 'text')
    if alert:
        if Registry().get('plugin_manager').get_plugin_by_name('alerts').status == PluginStatus.Active:
            Registry().get('alerts_manager').alerts_text.emit([alert])
    return old_success_response()


@plugins.route('/images/list', methods=['GET'])
def list_images():
    """
    Return the list of images in OpenLP's Images library with base64 thumbnail previews.
    """
    log.debug('images/list called')
    plugin = Registry().get('plugin_manager').get_plugin_by_name('images')
    if not plugin or plugin.status != PluginStatus.Active or not plugin.media_item:
        return jsonify([])

    from openlp.plugins.images.lib.db import Item
    media_item = plugin.media_item
    items = media_item.manager.get_all_objects(Item, order_by_ref=Item.file_path)
    result = []
    for item in items:
        file_path = Path(item.file_path)
        if not file_path.exists():
            continue
        thumb_path = media_item.generate_thumbnail_path(item)
        if not thumb_path.exists():
            try:
                create_thumb(file_path, thumb_path)
            except Exception:
                pass
        thumb_uri = image_to_data_uri(thumb_path) if thumb_path.exists() else image_to_data_uri(file_path)
        result.append({
            'id': str(file_path),
            'db_id': item.id,
            'filename': file_path.name,
            'title': file_path.name,
            'thumbnail': thumb_uri
        })
    return jsonify(result)


@plugins.route('/images/upload', methods=['POST'])
@login_required
def upload_image():
    """
    Upload an image directly from the mobile device's gallery into OpenLP's Images library,
    and optionally load it into Preview, Live, or Service.
    """
    log.debug('images/upload called')
    plugin = Registry().get('plugin_manager').get_plugin_by_name('images')
    if not plugin or plugin.status != PluginStatus.Active or not plugin.media_item:
        abort(400)

    filename = ''
    raw_bytes = None
    action = 'library'

    if request.is_json and request.json:
        data = request.json
        filename = data.get('filename', '')
        action = data.get('action', 'library')
        b64_data = data.get('data', '')
        if not b64_data:
            abort(400)
        if ',' in b64_data:
            b64_data = b64_data.split(',', 1)[1]
        try:
            raw_bytes = base64.b64decode(b64_data)
        except Exception:
            abort(400)
    elif 'file' in request.files:
        uploaded_file = request.files['file']
        filename = uploaded_file.filename or ''
        raw_bytes = uploaded_file.read()
        action = request.form.get('action', 'library')
    else:
        abort(400)

    if not raw_bytes:
        abort(400)

    safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', Path(filename).name) if filename else ''
    if not safe_name or '.' not in safe_name:
        safe_name = f'mobile_{int(time.time())}.jpg'

    upload_dir = AppLocation.get_section_data_path('images') / 'mobile_uploads'
    create_paths(upload_dir)
    dest_path = upload_dir / safe_name
    if dest_path.exists():
        stem = dest_path.stem
        suffix = dest_path.suffix
        dest_path = upload_dir / f'{stem}_{int(time.time())}{suffix}'

    dest_path.write_bytes(raw_bytes)

    from openlp.plugins.images.lib.db import Item
    media_item = plugin.media_item

    def _register_and_trigger():
        existing = media_item.manager.get_object_filtered(Item, Item.file_path == str(dest_path))
        if not existing:
            file_hash = sha256_file_hash(dest_path)
            new_item = Item(name=str(dest_path), file_path=str(dest_path), file_hash=file_hash)
            media_item.manager.save_object(new_item)
        else:
            new_item = existing
        thumb_path = media_item.generate_thumbnail_path(new_item)
        create_thumb(dest_path, thumb_path)
        media_item.load_list(
            media_item.manager.get_all_objects(Item, order_by_ref=Item.file_path), is_initial_load=True)
        if action == 'preview':
            tree_item = media_item.create_item_from_id(str(dest_path))
            srv_item = media_item.build_service_item(tree_item, remote=True, context=ServiceItemContext.Preview)
            if srv_item:
                srv_item.from_plugin = True
                Registry().get('preview_controller').add_service_item(srv_item)
        elif action == 'live':
            media_item.go_live(str(dest_path), remote=True)
        elif action == 'service':
            tree_item = media_item.create_item_from_id(str(dest_path))
            media_item.add_to_service(tree_item, remote=True)
        return thumb_path

    thumb_path = call_on_main_thread(_register_and_trigger)
    thumb_uri = image_to_data_uri(thumb_path) if thumb_path and thumb_path.exists() else image_to_data_uri(dest_path)
    return jsonify({
        'id': str(dest_path),
        'filename': dest_path.name,
        'title': dest_path.name,
        'thumbnail': thumb_uri
    }), 201


@plugins.route('/custom/list', methods=['GET'])
def list_custom_slides():
    """
    Return all custom slides with their parsed text verses.
    """
    log.debug('custom/list called')
    plugin = Registry().get('plugin_manager').get_plugin_by_name('custom')
    if not plugin or plugin.status != PluginStatus.Active:
        return jsonify([])

    from openlp.plugins.custom.lib.db import CustomSlide
    from openlp.plugins.custom.lib.customxmlhandler import CustomXML
    slides = plugin.db_manager.get_all_objects(CustomSlide, order_by_ref=CustomSlide.title)
    result = []
    for slide in slides:
        verses = [v[1] for v in CustomXML(slide.text).get_verses()]
        result.append({
            'id': slide.id,
            'title': slide.title,
            'slides': verses,
            'text': '\n---\n'.join(verses),
            'credits': slide.credits or '',
            'theme_name': slide.theme_name or ''
        })
    return jsonify(result)


@plugins.route('/custom/save', methods=['POST'])
@login_required
def save_custom_slide():
    """
    Create or update a Custom Slide from the mobile remote and optionally preview or project it.
    """
    log.debug('custom/save called')
    data = request.json
    if not data:
        abort(400)
    plugin = Registry().get('plugin_manager').get_plugin_by_name('custom')
    if not plugin or plugin.status != PluginStatus.Active or not plugin.media_item:
        abort(400)

    title = (data.get('title') or '').strip()
    raw_text = (data.get('text') or '').strip()
    slides_list = data.get('slides')
    if not title:
        abort(400)
    if not slides_list:
        slides_list = [s.strip() for s in re.split(r'\n---+\n', raw_text) if s.strip()] or [raw_text or title]

    credits = (data.get('credits') or '').strip()
    theme_name = (data.get('theme_name') or '').strip()
    custom_id = data.get('id')
    action = data.get('action', 'save')

    from openlp.plugins.custom.lib.db import CustomSlide
    from openlp.plugins.custom.lib.customxmlhandler import CustomXML

    custom_xml = CustomXML()
    for idx, slide_text in enumerate(slides_list):
        custom_xml.add_verse_to_lyrics('custom', str(idx + 1), slide_text)
    xml_string = str(custom_xml.extract_xml(), 'utf-8')

    def _save_and_trigger():
        custom_obj = None
        if custom_id:
            custom_obj = plugin.db_manager.get_object(CustomSlide, int(custom_id))
        if custom_obj:
            custom_obj.title = title
            custom_obj.text = xml_string
            custom_obj.credits = credits
            custom_obj.theme_name = theme_name
        else:
            custom_obj = CustomSlide(title=title, text=xml_string, credits=credits, theme_name=theme_name)
        plugin.db_manager.save_object(custom_obj)
        plugin.media_item.load_list()

        if action == 'preview':
            item = plugin.media_item.create_item_from_id(custom_obj.id)
            srv_item = plugin.media_item.build_service_item(item, remote=True, context=ServiceItemContext.Preview)
            if srv_item:
                srv_item.from_plugin = True
                Registry().get('preview_controller').add_service_item(srv_item)
        elif action == 'live':
            plugin.media_item.go_live(custom_obj.id, remote=True)
        elif action == 'service':
            item = plugin.media_item.create_item_from_id(custom_obj.id)
            plugin.media_item.add_to_service(item, remote=True)
        return custom_obj.id

    saved_id = call_on_main_thread(_save_and_trigger)
    return jsonify({
        'id': saved_id,
        'title': title,
        'slides': slides_list,
        'credits': credits,
        'theme_name': theme_name
    }), 200


@plugins.route('/bibles/books', methods=['GET'])
def list_bible_books():
    """
    Return the list of books and chapter counts for the active Bible in OpenLP.
    """
    log.debug('bibles/books called')
    plugin = Registry().get('plugin_manager').get_plugin_by_name('bibles')
    if not plugin or plugin.status != PluginStatus.Active or not plugin.media_item:
        return jsonify({'primary_bible': '', 'bibles': [], 'books': []})

    media_item = plugin.media_item
    bibles = list(plugin.manager.get_bibles().keys())
    primary = Registry().get('settings').value('bibles/primary bible') or (bibles[0] if bibles else '')
    books_data = []
    bible_db = media_item.bible or (plugin.manager.get_bibles().get(primary) if primary else None)
    if bible_db:
        try:
            lang_sel = plugin.manager.get_language_selection(bible_db.name)
            for book in bible_db.get_books():
                chapter_count = plugin.manager.get_chapter_count(bible_db.name, book)
                books_data.append({
                    'name': book.get_name(lang_sel),
                    'abbreviation': getattr(book, 'abbreviation', ''),
                    'chapters': chapter_count
                })
        except Exception:
            log.exception('Unable to list Bible books')
    return jsonify({
        'primary_bible': bible_db.name if bible_db else primary,
        'bibles': bibles,
        'books': books_data
    })

