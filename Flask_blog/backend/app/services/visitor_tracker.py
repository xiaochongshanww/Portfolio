"""访客统计追踪服务"""

import hashlib
from datetime import datetime, date
from sqlalchemy import func, and_
from sqlalchemy.exc import IntegrityError
from flask import request
from .. import db
from ..models import VisitorStats, DailyStats, SHANGHAI_TZ
import logging

logger = logging.getLogger(__name__)


class VisitorTracker:
    """访客统计追踪器"""
    
    @staticmethod
    def get_client_ip():
        """获取客户端真实IP地址"""
        # 按优先级检查各种代理头
        if request.headers.get('X-Forwarded-For'):
            # X-Forwarded-For可能包含多个IP，取第一个
            return request.headers.get('X-Forwarded-For').split(',')[0].strip()
        elif request.headers.get('X-Real-IP'):
            return request.headers.get('X-Real-IP')
        elif request.headers.get('X-Client-IP'):
            return request.headers.get('X-Client-IP')
        else:
            return request.remote_addr or '127.0.0.1'
    
    @staticmethod
    def get_user_agent_hash():
        """获取User-Agent的哈希值"""
        user_agent = request.headers.get('User-Agent', '')
        return hashlib.sha256(user_agent.encode('utf-8')).hexdigest()
    
    @staticmethod
    def track_visit():
        """记录访问，返回是否为今日新访客"""
        try:
            ip_address = VisitorTracker.get_client_ip()
            user_agent_hash = VisitorTracker.get_user_agent_hash()
            today = datetime.now(SHANGHAI_TZ).date()
            now = datetime.now(SHANGHAI_TZ)
            
            logger.info(f"Visitor tracking: IP={ip_address}, UA_Hash={user_agent_hash[:8]}..., Date={today}")
            
            # 查找今日该IP+User-Agent的记录
            visitor = VisitorStats.query.filter_by(
                ip_address=ip_address,
                user_agent_hash=user_agent_hash,
                visited_date=today
            ).first()
            
            logger.info(f"Existing record query result: {visitor is not None}")
            
            is_new_visitor = False
            
            if visitor:
                # 已存在记录，更新页面浏览量和最后访问时间
                logger.info(f"Updating existing visitor record: original page views={visitor.page_views}")
                visitor.page_views += 1
                visitor.last_visit_time = now
                logger.info(f"New page views={visitor.page_views}")
            else:
                # 新访客，创建记录
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
                logger.info(f"New visitor added to session: is_new_visitor={is_new_visitor}")
            
            logger.info("Committing database transaction...")
            db.session.commit()
            logger.info("Database transaction committed successfully")
            
            # 更新每日统计
            logger.info("Updating daily statistics...")
            VisitorTracker.update_daily_stats(today, is_new_visitor)
            
            return is_new_visitor
            
        except IntegrityError:
            # 并发情况下可能出现重复插入，回滚并重试
            db.session.rollback()
            return VisitorTracker._retry_track_visit()
        except Exception as e:
            db.session.rollback()
            print(f"访客统计记录失败: {str(e)}")
            return False
    
    @staticmethod
    def _retry_track_visit():
        """重试访问记录（处理并发情况）"""
        try:
            ip_address = VisitorTracker.get_client_ip()
            user_agent_hash = VisitorTracker.get_user_agent_hash()
            today = datetime.now(SHANGHAI_TZ).date()
            now = datetime.now(SHANGHAI_TZ)
            
            # 再次查找，此时应该已存在
            visitor = VisitorStats.query.filter_by(
                ip_address=ip_address,
                user_agent_hash=user_agent_hash,
                visited_date=today
            ).first()
            
            if visitor:
                visitor.page_views += 1
                visitor.last_visit_time = now
                db.session.commit()
            
            return False  # 重试时不算新访客
        except Exception as e:
            db.session.rollback()
            print(f"访客统计重试失败: {str(e)}")
            return False
    
    @staticmethod
    def update_daily_stats(target_date, is_new_visitor):
        """更新每日统计汇总"""
        try:
            daily_stat = DailyStats.query.filter_by(stat_date=target_date).first()
            
            if daily_stat:
                # 更新现有记录
                if is_new_visitor:
                    daily_stat.unique_visitors += 1
                daily_stat.total_page_views += 1
                daily_stat.updated_at = datetime.now(SHANGHAI_TZ)
            else:
                # 创建新记录
                daily_stat = DailyStats(
                    stat_date=target_date,
                    unique_visitors=1 if is_new_visitor else 0,
                    total_page_views=1,
                    created_at=datetime.now(SHANGHAI_TZ),
                    updated_at=datetime.now(SHANGHAI_TZ)
                )
                db.session.add(daily_stat)
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            print(f"每日统计更新失败: {str(e)}")
    
    @staticmethod
    def get_today_stats():
        """获取今日统计数据"""
        try:
            today = datetime.now(SHANGHAI_TZ).date()
            daily_stat = DailyStats.query.filter_by(stat_date=today).first()
            
            if daily_stat:
                return {
                    'today_visitors': daily_stat.unique_visitors,
                    'today_page_views': daily_stat.total_page_views
                }
            else:
                return {
                    'today_visitors': 0,
                    'today_page_views': 0
                }
        except Exception as e:
            print(f"获取今日统计失败: {str(e)}")
            return {
                'today_visitors': 0,
                'today_page_views': 0
            }
    
    @staticmethod
    def get_total_stats():
        """获取总计统计数据"""
        try:
            # 计算总访客数（所有日期的不重复IP+User-Agent组合）
            # 使用字符串拼接操作符 || (兼容SQLite和MySQL)
            total_visitors = db.session.query(
                func.count(func.distinct(VisitorStats.ip_address + VisitorStats.user_agent_hash))
            ).scalar() or 0
            
            # 计算总页面浏览量
            total_page_views = db.session.query(func.sum(DailyStats.total_page_views)).scalar() or 0
            
            return {
                'total_visitors': int(total_visitors),
                'total_page_views': int(total_page_views)
            }
        except Exception as e:
            print(f"获取总计统计失败: {str(e)}")
            return {
                'total_visitors': 0,
                'total_page_views': 0
            }
    
    @staticmethod
    def get_visitor_stats():
        """获取完整的访客统计数据"""
        today_stats = VisitorTracker.get_today_stats()
        total_stats = VisitorTracker.get_total_stats()
        
        return {
            'today_visitors': today_stats['today_visitors'],
            'today_page_views': today_stats['today_page_views'],
            'total_visitors': total_stats['total_visitors'],
            'total_page_views': total_stats['total_page_views']
        }