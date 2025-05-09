"""
測試路由註冊功能
"""
from tests.conftest import dummy_asgi_app


class TestRouteRegistration:
    """測試路由註冊功能"""
    
    def test_adding_routes(self, cy_router):
        """測試路由器的路由註冊功能"""
        # 註冊一些路由
        cy_router.add_route("/", dummy_asgi_app)
        cy_router.add_route("/users", dummy_asgi_app)
        cy_router.add_route("/users/{id}", dummy_asgi_app)
        cy_router.add_route("/users/{id}/posts", dummy_asgi_app)
        
        # 檢查註冊是否成功 (透過查找)
        app, params = cy_router.find_route("/")
        assert app is not None
        
        app, params = cy_router.find_route("/users")
        assert app is not None
        
        app, params = cy_router.find_route("/users/123")
        assert app is not None
        
        app, params = cy_router.find_route("/users/123/posts")
        assert app is not None
    
    def test_different_handlers(self, cy_router):
        """測試註冊不同的處理程序"""
        # 註冊不同的處理程序，以區分匹配結果
        def root_app(scope, receive, send):
            return None
            
        def users_app(scope, receive, send):
            return None
            
        def user_detail_app(scope, receive, send):
            return None
        
        cy_router.add_route("/", root_app)
        cy_router.add_route("/users", users_app)
        cy_router.add_route("/users/{user_id}", user_detail_app)
        
        # 驗證正確的處理程序被註冊
        app, _ = cy_router.find_route("/")
        assert app is root_app
        
        app, _ = cy_router.find_route("/users")
        assert app is users_app
        
        app, _ = cy_router.find_route("/users/123")
        assert app is user_detail_app
    
    def test_multiple_registrations(self, cy_router):
        """測試多次註冊相同路徑的行為"""
        def first_app(scope, receive, send):
            return None
            
        def second_app(scope, receive, send):
            return None
        
        # 首次註冊
        cy_router.add_route("/test", first_app)
        app, _ = cy_router.find_route("/test")
        assert app is first_app
        
        # 再次註冊同一路徑 (應覆蓋)
        cy_router.add_route("/test", second_app)
        app, _ = cy_router.find_route("/test")
        assert app is second_app
