"""
測試路徑正規化功能
"""

class TestPathNormalization:
    """測試路徑正規化邏輯"""
    
    def test_path_normalization(self, cy_router):
        """測試路徑正規化功能"""
        test_cases = [
            # 輸入路徑, 預期結果 (是否應該能找到路由)
            ("", True),
            ("/", True),
            ("//", True),
            ("/users", True),
            ("users/", True),
            ("/users/", True),
            ("/users//posts", True),
            ("/users/{id}/posts", True),
        ]
        
        # 為每個測試路徑註冊處理程序
        for path, _ in test_cases:
            def handler(scope, receive, send):
                return None
            cy_router.add_route(path, handler)
        
        # 測試每個路徑是否能被正確匹配
        for path, expected_found in test_cases:
            app, _ = cy_router.find_route(path)
            if expected_found:
                assert app is not None, f"路徑 '{path}' 應該被找到"
            else:
                assert app is None, f"路徑 '{path}' 不應該被找到"
    
    def test_equivalent_paths(self, cy_router):
        """測試等效路徑的正規化"""
        # 註冊單一路徑
        def handler(scope, receive, send):
            return None
        
        cy_router.add_route("/users", handler)
        
        # 測試等效路徑
        equivalent_paths = [
            "/users",
            "/users/",
            "users",
            "users/"
        ]
        
        for path in equivalent_paths:
            app, _ = cy_router.find_route(path)
            assert app is not None, f"等效路徑 '{path}' 應該匹配到 '/users'"
            
    def test_path_normalization_with_params(self, cy_router):
        """測試帶參數的路徑正規化"""
        # 註冊帶參數的路徑
        def handler(scope, receive, send):
            return None
        
        cy_router.add_route("/users/{user_id}", handler)
        
        # 測試參數匹配
        app, params = cy_router.find_route("/users/123")
        assert app is not None, "帶參數的路徑應該被找到"
        assert params == {"user_id": "123"}, "應正確提取參數值"
