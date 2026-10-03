"""Frontend routes and public portal address dispatch."""
import os
from flask import jsonify, render_template, send_from_directory


def register_frontend(app, frontend_dir):
    @app.before_request
    def serve_portal_address():
        from flask import request
        from ..utils.portal import portal_path
        from ..utils.helpdesk import helpdesk_path
        path = request.path.rstrip('/')
        if request.method in ('GET', 'HEAD') and path and not path.startswith('/api/') and '.' not in path:
            if path == portal_path():
                return send_from_directory(frontend_dir, 'portal.html')
            if path == helpdesk_path():
                return send_from_directory(frontend_dir, 'helpdesk.html')

    @app.route('/')
    @app.route('/index.html')
    def index():
        return render_template('index.html')

    @app.route('/<path:path>')
    def static_files(path):
        if path.startswith('api/'):
            return jsonify({'error': 'Nie znaleziono endpointu API.'}), 404
        full = os.path.join(frontend_dir, path)
        if os.path.exists(full):
            return send_from_directory(frontend_dir, path)
        return render_template('index.html')
