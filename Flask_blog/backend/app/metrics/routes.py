from flask import Blueprint, jsonify
from .. import db, require_roles
from ..models import User, Article, Comment, Tag, Category

metrics_bp = Blueprint('metrics', __name__)

@metrics_bp.route('/summary', methods=['GET'])
@require_roles('editor', 'admin')
def get_summary_stats():
    """获取全站核心统计数据。"""
    try:
        users_count = db.session.query(User.id).count()
        
        articles_total = db.session.query(Article.id).filter_by(deleted=False).count()
        articles_published = db.session.query(Article.id).filter_by(deleted=False, status='published').count()
        articles_draft = db.session.query(Article.id).filter_by(deleted=False, status='draft').count()
        articles_pending = db.session.query(Article.id).filter_by(deleted=False, status='pending').count()

        comments_total = db.session.query(Comment.id).count()
        comments_pending = db.session.query(Comment.id).filter_by(status='pending').count()
        comments_approved = db.session.query(Comment.id).filter_by(status='approved').count()

        tags_count = db.session.query(Tag.id).count()
        categories_count = db.session.query(Category.id).count()

        payload = {
            'users': {
                'total': users_count,
            },
            'articles': {
                'total': articles_total,
                'published': articles_published,
                'draft': articles_draft,
                'pending': articles_pending,
            },
            'comments': {
                'total': comments_total,
                'pending': comments_pending,
                'approved': comments_approved,
            },
            'taxonomy': {
                'tags': tags_count,
                'categories': categories_count,
            }
        }
        return jsonify({'code': 0, 'message': 'ok', 'data': payload})
    except Exception as e:
        return jsonify({'code': 5000, 'message': f'server error: {str(e)}'}), 500
