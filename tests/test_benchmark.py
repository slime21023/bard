"""
效能基準測試
測量 Cython 實現的路由器效能
"""
import pytest

from tests.conftest import dummy_asgi_app


class TestBenchmark:
    """效能基準測試"""
    
    @pytest.fixture(autouse=True)
    def setup_router(self, cy_router, sample_routes):
        """為每個測試準備路由器設置"""
        # 跳過測試如果 Cython 路由器不可用
        if cy_router.__class__.__name__ == 'function':
            pytest.skip("Cython 實現不可用，跳過基準測試")
        
        # 註冊路由
        for route in sample_routes:
            cy_router.add_route(route, dummy_asgi_app)
        
        # 提供給測試方法
        self.router = cy_router
    
    def test_registration_performance(self, benchmark):
        """測試路由註冊性能"""
        NUM_ROUTES = 1000
        routes = [f"/route/{i}" for i in range(NUM_ROUTES)]
        routes.extend([f"/param/{i}/{{id}}" for i in range(NUM_ROUTES)])
        
        # Cython 實現
        from bard import CythonASGITrieRouter
        
        def register():
            router = CythonASGITrieRouter()
            for route in routes:
                router.add_route(route, dummy_asgi_app)
            return router
        
        # 執行基準測試
        result = benchmark.pedantic(register, iterations=5, rounds=3)
        print(f"註冊 {len(routes)} 條路由平均耗時: {result.stats.mean:.6f} 秒")
    
    def test_lookup_performance(self, benchmark, test_paths):
        """測試路由查找性能"""
        # 準備查找測試
        def lookup():
            for path in test_paths:
                self.router.find_route(path)
        
        # 執行基準測試
        result = benchmark.pedantic(lookup, iterations=1000, rounds=5)
        print(f"查找 {len(test_paths)} 條靜態路由平均耗時: {result.stats.mean:.6f} 秒")
    
    def test_lookup_with_params_performance(self, benchmark):
        """測試具有參數的路由查找性能"""
        param_paths = [
            "/users/123",
            "/users/456/profile",
            "/users/789/posts",
            "/posts/101/comments/202",
            "/categories/303/posts"
        ]
        
        # 準備查找測試
        def lookup_params():
            for path in param_paths:
                self.router.find_route(path)
        
        # 執行基準測試
        result = benchmark.pedantic(lookup_params, iterations=1000, rounds=5)
        print(f"查找 {len(param_paths)} 條參數化路由平均耗時: {result.stats.mean:.6f} 秒")
    
    def test_iteration_performance(self, benchmark):
        """測試路由遍歷性能"""
        # 準備遍歷測試
        def iterate():
            list(self.router.iter_routes())
        
        # 執行基準測試
        result = benchmark.pedantic(iterate, iterations=100, rounds=5)
        routes_count = len(list(self.router.iter_routes()))
        print(f"遍歷 {routes_count} 條路由平均耗時: {result.stats.mean:.6f} 秒")
    
    def test_bulk_operations(self, benchmark):
        """測試批量操作性能"""
        NUM_ITERATIONS = 10000
        urls = ["/test/route/1", "/test/users/123", "/test/posts/456/comments", "/test/categories/789"]
        
        def bulk_operations():
            for _ in range(NUM_ITERATIONS // len(urls)):
                for url in urls:
                    self.router.find_route(url)
        
        # 執行基準測試
        result = benchmark.pedantic(bulk_operations, iterations=3, rounds=3)
        print(f"批量查找 {NUM_ITERATIONS} 次平均耗時: {result.stats.mean:.6f} 秒")
        print(f"每次查找平均耗時: {result.stats.mean * 1000000 / NUM_ITERATIONS:.6f} 微秒")
