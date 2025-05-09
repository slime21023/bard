"""
測試路由遍歷功能
"""

class TestRouteIteration:
    """測試遍歷所有註冊的路由功能"""
    
    def test_iterating_routes(self, cy_router):
        """測試路由遍歷功能"""
        # 註冊一些路由
        def app1(scope, receive, send):
            return None
            
        def app2(scope, receive, send):
            return None
            
        def app3(scope, receive, send):
            return None
        
        cy_router.add_route("/", app1)
        cy_router.add_route("/users", app2)
        cy_router.add_route("/users/{id}", app3)
        
        # 收集所有路由
        routes = list(cy_router.iter_routes())
        
        # 驗證數量
        assert len(routes) == 3
        
        # 驗證內容 (路徑和應用程式)
        paths = [route[0] for route in routes]
        assert "/" in paths
        assert "/users" in paths
        assert "/users/{id}" in paths
        
        # 驗證處理程序與路徑的對應關係
        for path, app in routes:
            if path == "/":
                assert app is app1
            elif path == "/users":
                assert app is app2
            elif path == "/users/{id}":
                assert app is app3
    
    def test_complex_route_iteration(self, cy_router):
        """測試複雜路由結構的遍歷"""
        # 註冊一些複雜的路由結構
        def root(scope, receive, send):
            return None
            
        def users(scope, receive, send):
            return None
            
        def user_detail(scope, receive, send):
            return None
            
        def user_posts(scope, receive, send):
            return None
            
        def post_comments(scope, receive, send):
            return None
        
        cy_router.add_route("/", root)
        cy_router.add_route("/users", users)
        cy_router.add_route("/users/{user_id}", user_detail)
        cy_router.add_route("/users/{user_id}/posts", user_posts)
        cy_router.add_route("/users/{user_id}/posts/{post_id}/comments", post_comments)
        
        # 收集所有路由
        routes = list(cy_router.iter_routes())
        
        # 驗證數量
        assert len(routes) == 5
        
        # 檢查所有路徑是否都被正確遍歷
        paths = [route[0] for route in routes]
        assert "/" in paths
        assert "/users" in paths
        assert "/users/{user_id}" in paths
        assert "/users/{user_id}/posts" in paths
        assert "/users/{user_id}/posts/{post_id}/comments" in paths
