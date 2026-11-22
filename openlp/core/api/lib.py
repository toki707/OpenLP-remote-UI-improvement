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
import json
import logging
import threading
from flask import jsonify, Response, request
from functools import wraps
from PyQt5 import QtCore
from openlp.core.common.registry import Registry

log = logging.getLogger(__name__)


class MainThreadDispatcher(QtCore.QObject):
    """
    Helper QObject to safely dispatch callables from HTTP worker threads onto the main Qt GUI thread.
    """
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
    """
    Execute ``fn`` on the main Qt GUI thread. If already on the main thread (or no QCoreApplication is running),
    executes synchronously.
    """
    global _dispatcher
    app = QtCore.QCoreApplication.instance()
    if app is None or QtCore.QThread.currentThread() == app.thread():
        return fn()
    if _dispatcher is None:
        _dispatcher = MainThreadDispatcher()
    event = threading.Event() if wait else None
    box = {'value': None, 'error': None}
    _dispatcher.execute_signal.emit((fn, event, box))
    if wait and event:
        event.wait(timeout)
        if box['error'] is not None:
            raise box['error']
        return box['value']
    return None



def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not Registry().get('settings_thread').value('api/authentication enabled'):
            return f(*args, **kwargs)
        token = request.headers.get('Authorization', '')
        if token == Registry().get('authentication_token'):
            return f(*args, **kwargs)
        else:
            return '', 401
    return decorated


def old_success_response():
    return jsonify({'results': {'success': True}})


def extract_request(json_string, name):
    try:
        if json_string:
            return json.loads(json_string)['request'][name]
    except KeyError:
        pass
    return None


# ----------------------- OLD AUTH SECTION ---------------------
def check_auth(username, password):
    return Registry().get('settings_thread').value('api/user id') == username and \
        Registry().get('settings_thread').value('api/password') == password


def old_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not Registry().get('settings_thread').value('api/authentication enabled'):
            return f(*args, **kwargs)
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return Response('', 401, {'WWW-Authenticate': 'Basic realm="OpenLP Login Required"'})
        else:
            return f(*args, **kwargs)
    return decorated
