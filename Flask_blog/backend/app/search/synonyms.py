from flask import Blueprint, request, jsonify
from .. import require_roles
from . import client as search_client

synonyms_bp = Blueprint('synonyms', __name__)

@synonyms_bp.route('/', methods=['GET'])
@require_roles('editor','admin')
def list_synonyms():
    try:
        idx = search_client.ensure_index()
        syns = idx.get_synonyms() or {}
        data = [{'term': k, 'synonyms': v} for k,v in syns.items()]
        return jsonify({'code':0,'data':data,'message':'ok'})
    except Exception:
        return jsonify({'code':5000,'message':'list failed'}), 500

@synonyms_bp.route('/', methods=['POST'])
@require_roles('editor','admin')
def add_synonym():
    js = request.get_json(force=True, silent=True) or {}
    term = (js.get('term') or '').strip()
    syns = js.get('synonyms') or []
    if not term or not isinstance(syns, list) or not syns:
        return jsonify({'code':4001,'message':'invalid payload'}), 400
    try:
        idx = search_client.ensure_index()
        existing = idx.get_synonyms() or {}
        existing[term] = syns
        idx.update_synonyms(existing)
        return jsonify({'code':0,'data':{'term':term,'synonyms':syns},'message':'ok'})
    except Exception:
        return jsonify({'code':5000,'message':'update failed'}), 500

@synonyms_bp.route('/<term>', methods=['DELETE'])
@require_roles('editor','admin')
def delete_synonym(term):
    term = (term or '').strip()
    if not term:
        return jsonify({'code':4001,'message':'term required'}), 400
    try:
        idx = search_client.ensure_index()
        existing = idx.get_synonyms() or {}
        if term in existing:
            existing.pop(term)
            idx.update_synonyms(existing)
        return jsonify({'code':0,'data':{'term':term},'message':'ok'})
    except Exception:
        return jsonify({'code':5000,'message':'delete failed'}), 500

__all__ = ['synonyms_bp']
