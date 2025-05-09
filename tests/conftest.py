"""
pytest 配置文件，為測試提供共享夾具
"""

import pytest

# 模擬 ASGI 應用程式，用於測試
async def dummy_asgi_app(scope, receive, send):
    """一個簡單的模擬 ASGI 應用程式，用於測試目的"""
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [(b'content-type', b'text/plain')]
    })
    await send({
        'type': 'http.response.body',
        'body': b'Hello, World!'
    })


@pytest.fixture
def cy_router():
    """提供路由器實例"""
    try:
        from bard import Router
        return Router()
    except ImportError:
        pytest.skip("路由器實現不可用，請先編譯模組")


@pytest.fixture
def sample_routes():
    """提供一組測試用的路由樣本"""
    return [
        "/",
        "/users",
        "/users/{id}",
        "/users/{id}/profile",
        "/users/{id}/posts",
        "/users/{id}/posts/{post_id}",
        "/posts",
        "/posts/{id}",
        "/posts/{id}/comments",
        "/posts/{id}/comments/{comment_id}",
        "/categories",
        "/categories/{id}",
        "/categories/{id}/posts",
        "/search",
        "/about",
        "/contact",
        "/login",
        "/register",
        "/logout",
        "/dashboard",
    ]


@pytest.fixture
def test_paths():
    """提供一組測試用的請求路徑樣本"""
    return [
        "/",
        "/users",
        "/users/123",
        "/users/123/profile",
        "/posts/456/comments/789",
        "/categories/10/posts",
        "/not/exist",
    ]
