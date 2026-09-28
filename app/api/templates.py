from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.template import Template
from ..schemas.template import TemplateSchema
from ..services.render_service import render_preview
from ..utils.sanitize import apply_payload, build_model

templates_bp = Blueprint('templates', __name__)
schema = TemplateSchema()
schema_many = TemplateSchema(many=True)


@templates_bp.route('', methods=['GET'])
@jwt_required()
def list_items():
    return jsonify(schema_many.dump(
        Template.query.order_by(Template.id.desc()).all())), 200


@templates_bp.route('/<int:item_id>', methods=['GET'])
@jwt_required()
def get_item(item_id):
    return jsonify(schema.dump(Template.query.get_or_404(item_id))), 200


@templates_bp.route('', methods=['POST'])
@jwt_required()
def create_item():
    data = request.get_json(silent=True) or {}
    try:
        tpl = build_model(Template, data)
        db.session.add(tpl)
        db.session.commit()
        return jsonify(schema.dump(tpl)), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@templates_bp.route('/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_item(item_id):
    tpl = Template.query.get_or_404(item_id)
    try:
        apply_payload(tpl, request.get_json(silent=True) or {})
        db.session.commit()
        return jsonify(schema.dump(tpl)), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@templates_bp.route('/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_item(item_id):
    tpl = Template.query.get_or_404(item_id)
    db.session.delete(tpl)
    db.session.commit()
    return jsonify({'message': 'Deleted'}), 200


@templates_bp.route('/preview', methods=['POST'])
@jwt_required()
def preview_inline():
    data = request.get_json(silent=True) or {}
    content = data.get('content', '')
    tpl_type = data.get('type', 'offer')
    try:
        return Response(render_preview(content, tpl_type), mimetype='text/html')
    except Exception as e:
        return Response(
            f'<pre style="color:red;padding:20px;font-family:monospace">'
            f'Błąd renderowania szablonu:\n\n{e}</pre>',
            mimetype='text/html', status=400,
        )


@templates_bp.route('/<int:item_id>/preview', methods=['GET'])
@jwt_required()
def preview_saved(item_id):
    tpl = Template.query.get_or_404(item_id)
    try:
        return Response(render_preview(tpl.content, tpl.type or 'offer'),
                        mimetype='text/html')
    except Exception as e:
        return Response(
            f'<pre style="color:red;padding:20px;font-family:monospace">'
            f'Błąd renderowania szablonu:\n\n{e}</pre>',
            mimetype='text/html', status=400,
        )
