"""
測試路由查找和參數提取功能
"""


class TestRouteFinding:
    """測試路由查找功能"""
    
    def test_finding_routes(self, cy_router):
        """測試路由查找功能"""
        # 註冊不同的處理程序，以區分匹配結果
        def root_app(scope, receive, send):
            return None
            
        def users_app(scope, receive, send):
            return None
            
        def user_detail_app(scope, receive, send):
            return None
            
        def user_posts_app(scope, receive, send):
            return None
        
        cy_router.add_route("/", root_app)
        cy_router.add_route("/users", users_app)
        cy_router.add_route("/users/{user_id}", user_detail_app)
        cy_router.add_route("/users/{user_id}/posts", user_posts_app)
        
        # 測試靜態路徑
        app, params = cy_router.find_route("/")
        assert app is root_app
        assert params == {}
        
        app, params = cy_router.find_route("/users")
        assert app is users_app
        assert params == {}
        
        # 測試參數路徑
        app, params = cy_router.find_route("/users/123")
        assert app is user_detail_app
        assert params == {"user_id": "123"}
        
        app, params = cy_router.find_route("/users/123/posts")
        assert app is user_posts_app
        assert params == {"user_id": "123"}
        
        # 測試不存在的路徑
        app, params = cy_router.find_route("/not/exists")
        assert app is None
        assert params is None


class TestParameterExtraction:
    """測試參數提取功能"""
    
    def test_parameter_extraction(self, cy_router):
        """測試參數提取功能"""
        def handler(scope, receive, send):
            return None
            
        cy_router.add_route("/users/{user_id}", handler)
        cy_router.add_route("/posts/{post_id}/comments/{comment_id}", handler)
        
        # 單一參數
        app, params = cy_router.find_route("/users/123")
        assert params == {"user_id": "123"}
        
        # 多個參數
        app, params = cy_router.find_route("/posts/456/comments/789")
        assert params == {"post_id": "456", "comment_id": "789"}
