"""
測試各種邊界情況
"""


class TestEdgeCases:
    """測試邊界情況處理"""
    
    def test_edge_cases(self, cy_router):
        """測試邊界情況處理"""
        def edge_app(scope, receive, send):
            return None
        
        # 空路徑和根路徑
        cy_router.add_route("", edge_app)
        app, params = cy_router.find_route("")
        assert app is edge_app
        
        cy_router.add_route("/", edge_app)
        app, params = cy_router.find_route("/")
        assert app is edge_app
        
        # 前綴衝突 (如果 /users 存在，但 /users/profile 不存在)
        cy_router.add_route("/users", edge_app)
        app, params = cy_router.find_route("/users/profile")
        assert app is None
        
        # 尾斜線處理
        cy_router.add_route("/trailing/slash/", edge_app)
        app, params = cy_router.find_route("/trailing/slash")
        assert app is edge_app  # 應該匹配 (去除尾斜線)
        
    def test_duplicate_parameters(self, cy_router):
        """測試重複參數路徑"""
        def user_handler(scope, receive, send):
            return None
            
        def item_handler(scope, receive, send):
            return None
        
        # 註冊具有相同參數名的不同路徑
        cy_router.add_route("/users/{id}", user_handler)
        cy_router.add_route("/items/{id}", item_handler)
        
        # 測試參數提取
        app, params = cy_router.find_route("/users/123")
        assert app is user_handler
        assert params == {"id": "123"}
        
        app, params = cy_router.find_route("/items/456")
        assert app is item_handler
        assert params == {"id": "456"}
        
    def test_special_characters(self, cy_router):
        """測試特殊字符處理"""
        def handler(scope, receive, send):
            return None
            
        # 測試路徑中包含特殊字符
        cy_router.add_route("/files/{filename}", handler)
        
        app, params = cy_router.find_route("/files/document.pdf")
        assert app is handler
        assert params == {"filename": "document.pdf"}
        
        app, params = cy_router.find_route("/files/image-123_456.png")
        assert app is handler
        assert params == {"filename": "image-123_456.png"}
