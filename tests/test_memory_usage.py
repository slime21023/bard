"""
記憶體使用測試
測試不同數量路由下的記憶體占用情況
"""
import pytest
import gc
import os
from tests.conftest import dummy_asgi_app

# 從環境變數決定是否啟用記憶體測試
PSUTIL_AVAILABLE = os.environ.get('ENABLE_MEMORY_TESTS', 'false').lower() == 'true'


def get_memory_usage():
    """獲取當前進程的記憶體使用量（MB）"""
    if not PSUTIL_AVAILABLE:
        pytest.skip("psutil 未安裝，跳過記憶體測試")
    import psutil
    process = psutil.Process()
    return process.memory_info().rss / (1024 * 1024)  # 轉換為 MB


class TestMemoryUsage:
    """測試不同場景下的記憶體使用情況"""
    
    def test_memory_with_increasing_routes(self, cy_router):
        """測試隨著路由數量增加的記憶體使用變化"""
        if not PSUTIL_AVAILABLE:
            pytest.skip("psutil 未安裝，跳過記憶體測試")
        
        # 測試不同數量的路由
        route_counts = [100, 500, 1000, 5000, 10000]
        memory_usage = {}
        
        # 初始記憶體基準
        gc.collect()  # 強制垃圾回收以獲得更準確的基準
        base_memory = get_memory_usage()
        
        for count in route_counts:
            # 註冊指定數量的路由
            for i in range(count):
                path = f"/static/route/{i}"
                cy_router.add_route(path, dummy_asgi_app)
            
            # 強制垃圾回收並測量記憶體
            gc.collect()
            memory_after = get_memory_usage()
            memory_usage[count] = memory_after - base_memory
            
            # 輸出結果
            print(f"\n註冊 {count} 條路由後的額外記憶體使用: {memory_usage[count]:.2f} MB")
            print(f"每條路由平均記憶體使用: {(memory_usage[count] * 1024) / count:.2f} KB")
        
        # 驗證記憶體使用隨路由數量增長，但增長率應該保持相對穩定
        for i in range(len(route_counts) - 1):
            count_ratio = route_counts[i+1] / route_counts[i]
            memory_ratio = memory_usage[route_counts[i+1]] / max(0.1, memory_usage[route_counts[i]])  # 避免除以零
            print(f"\n路由數量增加比例: {count_ratio:.1f}x, 記憶體增加比例: {memory_ratio:.1f}x")
            
            # 記憶體使用增長不應該顯著超過路由數量增長（允許一定誤差）
            assert memory_ratio <= count_ratio * 1.5, "記憶體使用增長過快"

    def test_memory_with_deep_routes(self, cy_router):
        """測試深度嵌套路由的記憶體使用情況"""
        if not PSUTIL_AVAILABLE:
            pytest.skip("psutil 未安裝，跳過記憶體測試")

        # 初始記憶體基準
        gc.collect()
        base_memory = get_memory_usage()
        
        # 創建不同深度的路由
        depths = [5, 10, 20, 50]
        memory_usage = {}
        
        for depth in depths:
            # 創建指定深度的路由
            for i in range(100):  # 每個深度創建 100 條路由
                # 生成深度路徑，例如 /d1/d2/d3/d4/d5
                path = "/" + "/".join([f"d{j}" for j in range(1, depth+1)])
                path = f"{path}/{i}"  # 添加唯一標識
                cy_router.add_route(path, dummy_asgi_app)
            
            # 測量記憶體
            gc.collect()
            memory_usage[depth] = get_memory_usage() - base_memory
            
            print(f"\n深度 {depth} 的路由（100條）的額外記憶體使用: {memory_usage[depth]:.2f} MB")
            print(f"每深度層級平均記憶體增加: {memory_usage[depth] / depth:.2f} MB")
    
    def test_memory_with_param_routes(self, cy_router):
        """測試參數化路由的記憶體使用情況"""
        if not PSUTIL_AVAILABLE:
            pytest.skip("psutil 未安裝，跳過記憶體測試")

        # 初始記憶體基準
        gc.collect()
        base_memory = get_memory_usage()
        
        # 比較靜態路由和參數化路由
        route_types = {
            "static": [f"/users/{i}" for i in range(1000)],
            "param": [f"/users/{{{i}}}" for i in range(1000)],
            "mixed": [f"/users/{i}/posts/{{{j}}}" for i in range(50) for j in range(20)]
        }
        
        memory_usage = {}
        
        for route_type, routes in route_types.items():
            # 註冊路由
            for route in routes:
                cy_router.add_route(route, dummy_asgi_app)
            
            # 測量記憶體
            gc.collect()
            memory_usage[route_type] = get_memory_usage() - base_memory
            
            print(f"\n{route_type} 路由（{len(routes)}條）的額外記憶體使用: {memory_usage[route_type]:.2f} MB")
            print(f"每條路由平均記憶體使用: {(memory_usage[route_type] * 1024) / len(routes):.2f} KB")
        
        # 驗證參數化路由的記憶體效率
        assert memory_usage["param"] <= memory_usage["static"] * 1.2, "參數化路由記憶體效率顯著低於靜態路由"
