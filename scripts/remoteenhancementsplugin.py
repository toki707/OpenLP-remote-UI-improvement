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
Community extension module that activates the enhanced Mobile Remote API v2 endpoints
and the Desktop Simplified Youth Mode toolbar inside an installed OpenLP instance.
"""
import base64
import json
import logging
import re
import threading
import time
from pathlib import Path

from flask import Blueprint, Response, abort, jsonify, request
from PyQt5 import QtCore, QtWidgets

from openlp.core.api import app as flask_app
from openlp.core.api.lib import login_required
from openlp.core.common import sha256_file_hash
from openlp.core.common.applocation import AppLocation
from openlp.core.common.json import OpenLPJSONEncoder
from openlp.core.common.path import create_paths
from openlp.core.common.registry import Registry
from openlp.core.common.utils import is_uuid
from openlp.core.lib import ServiceItemContext, create_thumb, image_to_data_uri
from openlp.core.lib.plugin import PluginStatus
from openlp.core.state import State

log = logging.getLogger(__name__)


class _MainThreadDispatcher(QtCore.QObject):
    execute_signal = QtCore.pyqtSignal(object)

    def __init__(self):
        super().__init__()
        app = QtCore.QCoreApplication.instance()
        if app and self.thread() != app.thread():
            self.moveToThread(app.thread())
        self.execute_signal.connect(self._on_execute)

    @QtCore.pyqtSlot(object)
    def _on_execute(self, task):
        fn, event, box = task
        try:
            box['value'] = fn()
        except Exception as exc:
            log.exception('Error executing API task on main thread')
            box['error'] = exc
        finally:
            if event:
                event.set()


_dispatcher = None


def call_on_main_thread(fn, wait=True, timeout=5.0):
    global _dispatcher
    app = QtCore.QCoreApplication.instance()
    if app is None or QtCore.QThread.currentThread() == app.thread():
        return fn()
    if _dispatcher is None:
        _dispatcher = _MainThreadDispatcher()
    event = threading.Event() if wait else None
    box = {'value': None, 'error': None}
    _dispatcher.execute_signal.emit((fn, event, box))
    if wait and event:
        event.wait(timeout)
        if box['error'] is not None:
            raise box['error']
        return box['value']
    return None


ext_bp = Blueprint('remote_ui_enhancements', __name__)


def _enrich_image_slides(service_item, item_dict):
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


@ext_bp.route('/api/v2/controller/preview-items')
def controller_preview_items():
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
    return Response(json.dumps(preview_item, cls=OpenLPJSONEncoder), mimetype='application/json')


@ext_bp.route('/api/v2/controller/preview/show', methods=['POST'])
@login_required
def controller_preview_set():
    data = request.json
    if not data:
        abort(400)
    num = data.get('id', -1)
    Registry().get('preview_controller').slidecontroller_preview_set.emit([num])
    return '', 204


@ext_bp.route('/api/v2/controller/preview/progress', methods=['POST'])
@login_required
def controller_preview_direction():
    data = request.json
    if not data:
        abort(400)
    action = data.get('action', '').lower()
    if action not in ['next', 'previous']:
        abort(400)
    getattr(Registry().get('preview_controller'), f'slidecontroller_preview_{action}').emit()
    return '', 204


@ext_bp.route('/api/v2/controller/preview/go-live', methods=['POST'])
@login_required
def controller_preview_go_live():
    preview_controller = Registry().get('preview_controller')
    if not preview_controller or not preview_controller.service_item:
        abort(400)
    call_on_main_thread(preview_controller.on_go_live)
    return '', 204


@ext_bp.route('/api/v2/service/preview', methods=['POST'])
@ext_bp.route('/api/v2/service/preview/<item_id>', methods=['POST'])
@login_required
def service_preview(item_id=None):
    data = request.json or {}
    item_id = item_id or data.get('id') or data.get('uid')
    if item_id is None or item_id == '':
        abort(400)
    service_manager = Registry().get('service_manager')
    preview_controller = Registry().get('preview_controller')
    if not service_manager or not preview_controller:
        abort(400)
    target_service_item = None
    if is_uuid(str(item_id)):
        for entry in service_manager.service_items:
            if str(entry['service_item'].unique_identifier) == str(item_id):
                target_service_item = entry['service_item']
                break
    else:
        try:
            idx = int(item_id)
            if 0 <= idx < len(service_manager.service_items):
                target_service_item = service_manager.service_items[idx]['service_item']
        except ValueError:
            abort(400)
    if not target_service_item:
        abort(404)
    call_on_main_thread(lambda: preview_controller.add_service_manager_item(target_service_item, 0))
    return '', 204


@ext_bp.route('/api/v2/plugins/<plugin_name>/preview', methods=['POST'])
@login_required
def plugin_preview(plugin_name):
    data = request.json
    if not data:
        abort(400)
    item_id = data.get('id', -1)
    plugin = Registry().get('plugin_manager').get_plugin_by_name(plugin_name)
    if plugin and plugin.status == PluginStatus.Active and plugin.media_item:
        def _do_preview():
            item = plugin.media_item.create_item_from_id(item_id)
            service_item = plugin.media_item.build_service_item(
                item, remote=True, context=ServiceItemContext.Preview)
            if service_item:
                service_item.from_plugin = True
                Registry().get('preview_controller').add_service_item(service_item)
        call_on_main_thread(_do_preview)
    return '', 204


@ext_bp.route('/api/v2/plugins/images/list', methods=['GET'])
def list_images():
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


@ext_bp.route('/api/v2/plugins/images/upload', methods=['POST'])
@login_required
def upload_image():
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
        raw_bytes = base64.b64decode(b64_data)
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
        dest_path = upload_dir / f'{dest_path.stem}_{int(time.time())}{dest_path.suffix}'
    dest_path.write_bytes(raw_bytes)
    from openlp.plugins.images.lib.db import Item
    media_item = plugin.media_item

    def _register_and_trigger():
        existing = media_item.manager.get_object_filtered(Item, Item.file_path == str(dest_path))
        if not existing:
            new_item = Item(name=str(dest_path), file_path=str(dest_path), file_hash=sha256_file_hash(dest_path))
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


@ext_bp.route('/api/v2/plugins/custom/list', methods=['GET'])
def list_custom_slides():
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


@ext_bp.route('/api/v2/plugins/custom/save', methods=['POST'])
@login_required
def save_custom_slide():
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


@ext_bp.route('/api/v2/plugins/bibles/books', methods=['GET'])
def list_bible_books():
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


try:
    if 'remote_ui_enhancements' not in flask_app.blueprints:
        flask_app.register_blueprint(ext_bp)
        log.info('Registered Remote UI v2 enhancement endpoints')
except Exception:
    log.exception('Unable to register Remote UI enhancement blueprint')


# Attach Simplified Youth Mode & Apple HIG Theme Switcher to MainWindow once startup finishes
YOUTH_ALLOWED_PLUGINS = ('bibles', 'images', 'custom', 'songs')

APPLE_DARK_QSS = """
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

APPLE_LIGHT_QSS = """
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


def _attach_pc_toolbar():
    main_window = Registry().get('main_window')
    if not main_window or hasattr(main_window, 'simplified_mode_toolbar'):
        return
    toolbar = QtWidgets.QToolBar('Accès Rapide Culte', main_window)
    toolbar.setObjectName('simplified_quick_bar')
    toolbar.setMovable(False)
    toolbar.setFloatable(False)

    label = QtWidgets.QLabel(' Bibliothèque : ', toolbar)
    font = label.font()
    font.setBold(True)
    label.setFont(font)
    toolbar.addWidget(label)

    quick_buttons = {}

    def focus_tab(plugin_name):
        if not main_window.media_manager_dock.isVisible():
            main_window.media_manager_dock.setVisible(True)
        tb = main_window.media_tool_box
        for idx in range(tb.count()):
            w = tb.widget(idx)
            if w and getattr(w, 'settings_section', '') == plugin_name:
                tb.setCurrentIndex(idx)
                break
        for k, b in quick_buttons.items():
            b.setChecked(k == plugin_name)

    for p_name, p_title in [('bibles', 'Bible'), ('images', 'Images & Affiches'),
                            ('custom', 'Diapos perso'), ('songs', 'Chants')]:
        btn = QtWidgets.QPushButton(p_title, toolbar)
        btn.setCheckable(True)
        btn.setCursor(QtCore.Qt.PointingHandCursor)
        btn.setMinimumHeight(30)
        btn.clicked.connect(lambda checked, p=p_name: focus_tab(p))
        toolbar.addWidget(btn)
        quick_buttons[p_name] = btn

    spacer = QtWidgets.QWidget(toolbar)
    spacer.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Preferred)
    toolbar.addWidget(spacer)

    simple_btn = QtWidgets.QPushButton('Mode Simplifié (Jeunes) : Désactivé', toolbar)
    simple_btn.setCheckable(True)
    simple_btn.setCursor(QtCore.Qt.PointingHandCursor)
    simple_btn.setMinimumHeight(30)

    def toggle_simple():
        active = simple_btn.isChecked()
        if active:
            simple_btn.setText('Mode Simplifié (Jeunes) : Actif')
            if hasattr(main_window, 'projector_manager_dock'):
                main_window.projector_manager_dock.setVisible(False)
            for plugin in State().list_plugins():
                if plugin and plugin.media_item and plugin.name not in YOUTH_ALLOWED_PLUGINS:
                    main_window.media_dock_manager.remove_dock(plugin.media_item)
            focus_tab('bibles')
        else:
            simple_btn.setText('Mode Simplifié (Jeunes) : Désactivé')
            for plugin in State().list_plugins():
                if plugin and plugin.status == PluginStatus.Active and plugin.media_item:
                    main_window.media_dock_manager.add_item_to_dock(plugin.media_item)

    simple_btn.clicked.connect(toggle_simple)
    toolbar.addWidget(simple_btn)

    theme_state = {'dark': False}
    theme_btn = QtWidgets.QPushButton('Thème : Clair (Apple)', toolbar)
    theme_btn.setCursor(QtCore.Qt.PointingHandCursor)
    theme_btn.setMinimumHeight(30)

    def apply_apple_theme(is_dark):
        app = QtWidgets.QApplication.instance()
        if not app:
            return
        try:
            from openlp.core.ui.style import set_default_darkmode, set_default_lightmode
            if is_dark:
                set_default_darkmode(app)
            else:
                set_default_lightmode(app)
        except Exception:
            pass
        qss = APPLE_DARK_QSS if is_dark else APPLE_LIGHT_QSS
        app.setStyleSheet(qss)
        main_window.setStyleSheet(qss)
        if hasattr(main_window, 'media_manager_dock') and main_window.media_manager_dock:
            main_window.media_manager_dock.setStyleSheet('')
        theme_btn.setText('Thème : Sombre (Noir)' if is_dark else 'Thème : Clair (Blanc)')

    def toggle_theme():
        theme_state['dark'] = not theme_state['dark']
        apply_apple_theme(theme_state['dark'])

    theme_btn.clicked.connect(toggle_theme)
    toolbar.addWidget(theme_btn)

    main_window.addToolBar(QtCore.Qt.TopToolBarArea, toolbar)
    main_window.simplified_mode_toolbar = toolbar
    apply_apple_theme(False)


try:
    Registry().register_function('bootstrap_post_set_up', _attach_pc_toolbar)
except Exception:
    pass
QtCore.QTimer.singleShot(1000, _attach_pc_toolbar)
