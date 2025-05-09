#!/usr/bin/env python3
"""
ASGI 中間件示例
展示如何將 Bard ASGI Trie Router 與其他 ASGI 框架集成

使用方法:
    uvicorn middleware_example:app --reload

需要安裝:
    pip install uvicorn starlette
"""

import time
from typing import Callable, Dict, Any, Optional

from starlette.applications import Starlette
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.requests import Request
from starlette.routing import Route

try:
    from bard import CythonASGITrieRouter
except ImportError:
    print("警告: 無法導入 Cython 路由器，使用 Python 版本")
    from bard.py_router import PyASGITrieRouter as CythonASGITrieRouter


# 創建路由器實例
router = CythonASGITrieRouter()


# 自定義 ASGI 處理程序（不使用 Starlette 路由）
async def api_users(scope, receive, send):
    """自定義 API 處理程序"""
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            (b'content-type', b'application/json'),
        ],
    })
    await send({
        'type': 'http.response.body',
        'body': b'{"users": ["user1", "user2", "user3"]}',
    })


async def api_user_detail(scope, receive, send):
    """自定義 API 用戶詳情處理程序"""
    # 從路由參數中獲取用戶名
    username = scope.get('route_params', {}).get('username', 'unknown')
    
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            (b'content-type', b'application/json'),
        ],
    })
    await send({
        'type': 'http.response.body',
        'body': f'{{"username": "{username}", "detail": "This is user {username}"}}'.encode('utf-8'),
    })


# 註冊自定義 API 路由
router.add_route("/api/users", api_users)
router.add_route("/api/users/{username}", api_user_detail)


# Starlette 路由處理程序
async def homepage(request):
    """首頁"""
    return PlainTextResponse(
        "Cython ASGI Router Middleware 示例\n"
        "可用路由:\n"
        "  /                         - 本頁面\n"
        "  /starlette/hello          - Starlette 處理的路由\n"
        "  /api/users                - 由自定義 ASGI 處理程序處理\n"
        "  /api/users/{username}     - 帶參數的自定義 ASGI 處理程序\n"
        "  /benchmark                - 路由性能基準測試\n"
    )


async def hello(request):
    """Starlette 處理的問候路由"""
    return JSONResponse({"message": "Hello from Starlette!"})


async def benchmark(request):
    """路由性能基準測試"""
    # 創建大量測試路由
    test_router_py = CythonASGITrieRouter()
    
    # 計時添加 1000 條靜態路由
    start_time = time.time()
    for i in range(1000):
        test_router_py.add_route(f"/test/route/{i}", lambda scope, receive, send: None)
    static_add_time = time.time() - start_time
    
    # 計時添加 1000 條參數化路由
    start_time = time.time()
    for i in range(1000):
        test_router_py.add_route(f"/test/param/{i}/{{id}}", lambda scope, receive, send: None)
    param_add_time = time.time() - start_time
    
    # 計時查找 10000 次隨機路由
    start_time = time.time()
    for i in range(10000):
        idx = i % 1000
        test_router_py.find_route(f"/test/route/{idx}")
    static_find_time = time.time() - start_time
    
    # 計時查找 10000 次隨機參數化路由
    start_time = time.time()
    for i in range(10000):
        idx = i % 1000
        test_router_py.find_route(f"/test/param/{idx}/123")
    param_find_time = time.time() - start_time
    
    return JSONResponse({
        "benchmark_results": {
            "static_routes_add_time": f"{static_add_time:.6f} 秒 (1000 條路由)",
            "param_routes_add_time": f"{param_add_time:.6f} 秒 (1000 條路由)",
            "static_routes_find_time": f"{static_find_time:.6f} 秒 (10000 次查找)",
            "param_routes_find_time": f"{param_find_time:.6f} 秒 (10000 次查找)",
            "static_find_avg": f"{static_find_time/10000*1000000:.2f} 微秒/查找",
            "param_find_avg": f"{param_find_time/10000*1000000:.2f} 微秒/查找",
        }
    })


# 創建 Starlette 應用程序
starlette_app = Starlette(routes=[
    Route("/", homepage),
    Route("/starlette/hello", hello),
    Route("/benchmark", benchmark),
])


# 路由中間件
class TrieRouterMiddleware:
    """
    使用 Cython ASGI Trie Router 的 ASGI 中間件
    結合自定義路由和其他 ASGI 框架
    """
    
    def __init__(self, app, router):
        self.app = app
        self.router = router
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            # 非 HTTP 請求交由下一個應用處理
            await self.app(scope, receive, send)
            return
        
        path = scope["path"]
        handler, params = self.router.find_route(path)
        
        if handler:
            # 由我們的路由器處理
            scope["route_params"] = params
            await handler(scope, receive, send)
        else:
            # 讓 Starlette 處理
            await self.app(scope, receive, send)


# 主 ASGI 應用
app = TrieRouterMiddleware(starlette_app, router)


if __name__ == "__main__":
    print("這個文件應該由 ASGI 伺服器執行，例如 uvicorn")
    print("使用方法：uvicorn middleware_example:app --reload")
