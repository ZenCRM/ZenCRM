"""Serwowanie wgranych avatarów."""
import os
from flask import Blueprint, send_from_directory, abort

avatars_bp = Blueprint('avatars', __name__)
AVATAR_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'uploads', 'avatars'))


@avatars_bp.route('/<path:filename>', methods=['GET'])
def serve(filename):
    # Podstawowe zabezpieczenie przed path traversal
    if '..' in filename or filename.startswith('/'):
        abort(404)
    full = os.path.join(AVATAR_DIR, filename)
    if not os.path.exists(full):
        abort(404)
    return send_from_directory(AVATAR_DIR, filename)
