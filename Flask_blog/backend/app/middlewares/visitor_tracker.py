"""访客追踪中间件"""

from flask import request, g
from ..services.visitor_tracker import VisitorTracker


class VisitorTrackingMiddleware:
    """访客追踪中间件 - 自动记录页面访问"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化中间件"""
        app.before_request(self.track_visitor)
    
    def track_visitor(self):
        """在每个请求前追踪访客"""
        try:
            # 只追踪GET请求，避免重复计数
            if request.method != 'GET':
                return
            
            # 排除API请求、静态资源等
            if self._should_skip_tracking():
                return
            
            # 异步记录访问，不阻塞请求
            is_new_visitor = VisitorTracker.track_visit()
            
            # 保存到请求上下文，供其他地方使用
            g.is_new_visitor = is_new_visitor
            
        except Exception as e:
            # 追踪失败不应影响正常请求
            print(f"访客追踪中间件错误: {str(e)}")
            g.is_new_visitor = False
    
    def _should_skip_tracking(self):
        """判断是否应该跳过追踪"""
        path = request.path.lower()
        
        # 跳过的路径模式
        skip_patterns = [
            '/api/',           # API请求
            '/admin/',         # 管理后台
            '/metrics/',       # 统计API
            '/static/',        # 静态文件
            '/uploads/',       # 上传文件
            '/favicon.ico',    # 网站图标
            '/robots.txt',     # 爬虫文件
            '/sitemap.xml',    # 站点地图
        ]
        
        # 跳过的文件扩展名
        skip_extensions = [
            '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.ico',
            '.svg', '.woff', '.woff2', '.ttf', '.eot', '.map'
        ]
        
        # 检查路径模式
        for pattern in skip_patterns:
            if pattern in path:
                return True
        
        # 检查文件扩展名
        for ext in skip_extensions:
            if path.endswith(ext):
                return True
        
        # 检查User-Agent，排除爬虫和工具
        user_agent = request.headers.get('User-Agent', '').lower()
        bot_patterns = ['bot', 'crawler', 'spider', 'scraper', 'curl', 'wget', 'postman']
        
        for pattern in bot_patterns:
            if pattern in user_agent:
                return True
        
        return False