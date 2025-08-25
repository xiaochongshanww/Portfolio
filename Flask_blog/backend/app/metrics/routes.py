from flask import Blueprint, jsonify, request
from .. import db, require_roles
from ..models import User, Article, Comment, Tag, Category
from ..services.visitor_tracker import VisitorTracker
import logging

metrics_bp = Blueprint('metrics', __name__)
logger = logging.getLogger(__name__)

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


@metrics_bp.route('/visitors', methods=['GET'])
def get_visitor_stats():
    """获取访客统计数据（公开接口，用于页脚显示）"""
    try:
        stats = VisitorTracker.get_visitor_stats()
        
        payload = {
            'today_visitors': stats['today_visitors'],
            'today_page_views': stats['today_page_views'], 
            'total_visitors': stats['total_visitors'],
            'total_page_views': stats['total_page_views']
        }
        
        return jsonify({'code': 0, 'message': 'ok', 'data': payload})
    except Exception as e:
        return jsonify({'code': 5000, 'message': f'server error: {str(e)}'}), 500


@metrics_bp.route('/track', methods=['POST'])
def track_visit():
    """记录访问（由前端页面调用）"""
    try:
        logger.info("Track API called")
        
        # 直接测试数据库操作
        from ..models import VisitorStats, DailyStats, SHANGHAI_TZ
        from datetime import datetime
        import hashlib
        
        ip_address = request.remote_addr or '127.0.0.1'
        user_agent = request.headers.get('User-Agent', '')
        user_agent_hash = hashlib.sha256(user_agent.encode('utf-8')).hexdigest()
        today = datetime.now(SHANGHAI_TZ).date()
        now = datetime.now(SHANGHAI_TZ)
        
        logger.info(f"Direct DB test: IP={ip_address}, UA={user_agent[:20]}..., Date={today}")
        
        # 查找现有记录
        visitor = VisitorStats.query.filter_by(
            ip_address=ip_address,
            user_agent_hash=user_agent_hash,
            visited_date=today
        ).first()
        
        is_new_visitor = False
        
        if visitor:
            logger.info(f"Found existing visitor, updating page views from {visitor.page_views}")
            visitor.page_views += 1
            visitor.last_visit_time = now
        else:
            logger.info("Creating new visitor record")
            visitor = VisitorStats(
                ip_address=ip_address,
                user_agent_hash=user_agent_hash,
                visited_date=today,
                first_visit_time=now,
                last_visit_time=now,
                page_views=1
            )
            db.session.add(visitor)
            is_new_visitor = True
        
        db.session.commit()
        logger.info("Database commit successful")
        
        return jsonify({
            'code': 0, 
            'message': 'ok',
            'data': {
                'tracked': True,
                'is_new_visitor': is_new_visitor
            }
        })
    except Exception as e:
        logger.error(f"Track API error: {str(e)}")
        return jsonify({'code': 5000, 'message': f'server error: {str(e)}'}), 500
