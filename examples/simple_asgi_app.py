#!/usr/bin/env python3
"""
簡單的 ASGI 應用程式示例
展示如何使用 Cython ASGI Trie Router

使用方法:
    uvicorn simple_asgi_app:app --reload

需要安裝:
    pip install uvicorn
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Callable

from bard import Router

# 創建路由器實例
router = Router()

# 定義 ASGI 應用處理程序

async def index(scope, receive, send):
    """首頁處理程序"""
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            (b'content-type', b'text/html; charset=utf-8'),
        ],
    })
    content = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Cython ASGI Trie Router 範例</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                h1 { color: #333; }
                ul { list-style-type: none; padding: 0; }
                li { margin-bottom: 10px; }
                a { color: #0066cc; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <h1>Cython ASGI Trie Router 範例</h1>
            <p>這是一個使用 Cython ASGI Trie Router 實現的簡單 ASGI 應用程式。</p>
            <h2>可用路由：</h2>
            <ul>
                <li><a href="/">/</a> - 首頁</li>
                <li><a href="/hello">/hello</a> - 簡單打招呼</li>
                <li><a href="/users">/users</a> - 用戶列表</li>
                <li><a href="/users/1">/users/{id}</a> - 特定用戶資訊</li>
                <li><a href="/time">/time</a> - 當前時間</li>
                <li><a href="/echo?message=hello">/echo?message=...</a> - 迴響訊息</li>
                <li><a href="/routes">/routes</a> - 顯示所有已註冊路由</li>
            </ul>
        </body>
    </html>
    """
    await send({
        'type': 'http.response.body',
        'body': content.encode('utf-8'),
    })


async def hello(scope, receive, send):
    """簡單問候處理程序"""
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            (b'content-type', b'text/plain; charset=utf-8'),
        ],
    })
    await send({
        'type': 'http.response.body',
        'body': b'Hello, World!',
    })


async def users_list(scope, receive, send):
    """用戶列表處理程序"""
    # 模擬用戶數據
    users = [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "email": "bob@example.com"},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com"},
    ]
    
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            (b'content-type', b'application/json'),
        ],
    })
    await send({
        'type': 'http.response.body',
        'body': json.dumps(users).encode('utf-8'),
    })


async def user_detail(scope, receive, send):
    """特定用戶詳細資訊處理程序"""
    # 從路由參數中獲取用戶 ID
    user_id = int(scope.get('route_params', {}).get('id', 0))
    
    # 模擬用戶數據
    users = {
        1: {"id": 1, "name": "Alice", "email": "alice@example.com", "role": "admin"},
        2: {"id": 2, "name": "Bob", "email": "bob@example.com", "role": "user"},
        3: {"id": 3, "name": "Charlie", "email": "charlie@example.com", "role": "user"},
    }
    
    if user_id in users:
        response_body = json.dumps(users[user_id])
        status = 200
    else:
        response_body = json.dumps({"error": "User not found"})
        status = 404
    
    await send({
        'type': 'http.response.start',
        'status': status,
        'headers': [
            (b'content-type', b'application/json'),
        ],
    })
    await send({
        'type': 'http.response.body',
        'body': response_body.encode('utf-8'),
    })


async def current_time(scope, receive, send):
    """當前時間處理程序"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            (b'content-type', b'text/plain; charset=utf-8'),
        ],
    })
    await send({
        'type': 'http.response.body',
        'body': f"Current time: {now}".encode('utf-8'),
    })


async def echo(scope, receive, send):
    """迴響處理程序"""
    # 解析查詢參數
    query_string = scope.get('query_string', b'').decode('utf-8')
    query_params = {}
    
    if query_string:
        for param in query_string.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                query_params[key] = value
    
    message = query_params.get('message', 'No message provided')
    
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            (b'content-type', b'text/plain; charset=utf-8'),
        ],
    })
    await send({
        'type': 'http.response.body',
        'body': f"Echo: {message}".encode('utf-8'),
    })


async def routes_list(scope, receive, send):
    """顯示所有已註冊路由"""
    routes = list(router.iter_routes())
    
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [
            (b'content-type', b'text/html; charset=utf-8'),
        ],
    })
    
    content = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>已註冊路由</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                h1 { color: #333; }
                table { border-collapse: collapse; width: 100%; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                tr:hover { background-color: #f5f5f5; }
            </style>
        </head>
        <body>
            <h1>已註冊路由</h1>
            <table>
                <tr>
                    <th>路徑</th>
                    <th>處理程序</th>
                </tr>
    """
    
    for path, handler in routes:
        handler_name = handler.__name__ if hasattr(handler, '__name__') else str(handler)
        content += f"<tr><td>{path}</td><td>{handler_name}</td></tr>\n"
    
    content += """
            </table>
            <p><a href="/">返回首頁</a></p>
        </body>
    </html>
    """
    
    await send({
        'type': 'http.response.body',
        'body': content.encode('utf-8'),
    })


async def not_found(scope, receive, send):
    """404 處理程序"""
    path = scope.get('path', '')
    
    await send({
        'type': 'http.response.start',
        'status': 404,
        'headers': [
            (b'content-type', b'text/html; charset=utf-8'),
        ],
    })
    
    content = f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>404 - 頁面未找到</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                h1 {{ color: #c00; }}
                .path {{ font-family: monospace; background-color: #f0f0f0; padding: 5px; }}
            </style>
        </head>
        <body>
            <h1>404 - 頁面未找到</h1>
            <p>您請求的路徑 <span class="path">{path}</span> 無法找到</p>
            <p><a href="/">返回首頁</a></p>
        </body>
    </html>
    """
    
    await send({
        'type': 'http.response.body',
        'body': content.encode('utf-8'),
    })


# 註冊路由
router.add_route("/", index)
router.add_route("/hello", hello)
router.add_route("/users", users_list)
router.add_route("/users/{id}", user_detail)
router.add_route("/time", current_time)
router.add_route("/echo", echo)
router.add_route("/routes", routes_list)


# 主 ASGI 應用
async def app(scope, receive, send):
    """
    主 ASGI 應用程式
    使用路由器分派請求到正確的處理程序
    """
    if scope["type"] != "http":
        await send({
            'type': 'http.response.start',
            'status': 400,
            'headers': [(b'content-type', b'text/plain')],
        })
        await send({
            'type': 'http.response.body',
            'body': b'Invalid ASGI scope type',
        })
        return
    
    path = scope["path"]
    handler, params = router.find_route(path)
    
    if handler:
        # 將路由參數添加到 scope 中
        scope["route_params"] = params
        await handler(scope, receive, send)
    else:
        # 處理 404
        await not_found(scope, receive, send)


if __name__ == "__main__":
    print("這個文件應該由 ASGI 伺服器執行，例如 uvicorn")
    print("使用方法：uvicorn simple_asgi_app:app --reload")
