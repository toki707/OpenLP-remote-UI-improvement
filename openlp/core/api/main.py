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

import os
from pathlib import Path

from flask import Blueprint, send_from_directory
from openlp.core.common.applocation import AppLocation
from openlp.core.common.mime import get_mime_type

main_views = Blueprint('main', __name__)
BUNDLED_REMOTE_DIR = Path(__file__).parent / 'remote_client'


def _get_remotes_dir():
    remotes_dir = AppLocation.get_section_data_path('remotes')
    if os.path.isfile(remotes_dir / 'index.html'):
        return remotes_dir
    if BUNDLED_REMOTE_DIR.is_dir():
        return BUNDLED_REMOTE_DIR
    return remotes_dir


@main_views.route('/', defaults={'path': ''})
@main_views.route('/<path>')
def index(path):
    remotes_dir = _get_remotes_dir()
    if path and os.path.isfile(remotes_dir / path):
        return send_from_directory(str(remotes_dir), path, mimetype=get_mime_type(path))
    else:
        return send_from_directory(str(remotes_dir), 'index.html', mimetype='text/html')


@main_views.route('/assets/<path:path>')
def assets(path):
    remotes_dir = _get_remotes_dir()
    return send_from_directory(str(remotes_dir / 'assets'), path, mimetype=get_mime_type(path))


@main_views.route('/stage/<path>/')
def stages(path):
    return send_from_directory(str(AppLocation.get_section_data_path('stages') / path),
                               'stage.html', mimetype='text/html')


@main_views.route('/stage/<path:path>/<file>')
def stage_assets(path, file):
    return send_from_directory(str(AppLocation.get_section_data_path('stages') / path),
                               file, mimetype=get_mime_type(file))
