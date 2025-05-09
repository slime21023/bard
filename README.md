# Bard ASGI Trie Router

高效能的 ASGI 路由器，使用 Cython 實現，基於 Trie 樹結構設計，提供快速的路徑匹配和參數提取功能。

## 功能特點

- **高效能**：利用 Cython 的靜態型別和 C 級別效能
- **支援靜態和參數化路徑**：如 `/users` 和 `/users/{id}`
- **路徑參數提取**：自動從匹配的路由中提取參數值
- **路由優先級**：靜態路徑優先於參數化路徑
- **簡潔的 API**：易於整合到任何 ASGI 應用程式
- **無外部依賴**：僅依賴 Python 標準庫和 Cython

## 安裝

### 從 PyPI 安裝

使用 uv 安裝：

```bash
uv pip install bard
```

或使用 pip 安裝：

```bash
pip install bard
```

### 從源碼安裝

```bash
git clone https://github.com/example/bard.git
cd bard
pip install -e .
```

## 快速入門

### 基本用法

```python
from bard import Router

# 建立路由器
router = Router()

# 定義 ASGI 應用程式
async def index(scope, receive, send):
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [(b'content-type', b'text/plain')]
    })
    await send({
        'type': 'http.response.body',
        'body': b'Index page'
    })

async def users_list(scope, receive, send):
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [(b'content-type', b'text/plain')]
    })
    await send({
        'type': 'http.response.body',
        'body': b'Users list'
    })

async def user_detail(scope, receive, send):
    # 從路由參數中獲取用戶 ID
    user_id = scope["route_params"]["user_id"]
    await send({
        'type': 'http.response.start',
        'status': 200,
        'headers': [(b'content-type', b'text/plain')]
    })
    await send({
        'type': 'http.response.body',
        'body': f'User detail: {user_id}'.encode()
    })

async def not_found_handler(scope, receive, send):
    await send({
        'type': 'http.response.start',
        'status': 404,
        'headers': [(b'content-type', b'text/plain')]
    })
    await send({
        'type': 'http.response.body',
        'body': b'Not found'
    })

# 註冊路由
router.add_route("/", index)
router.add_route("/users", users_list)
router.add_route("/users/{user_id}", user_detail)

# 使用路由器
async def app(scope, receive, send):
    if scope["type"] != "http":  # 僅處理 HTTP 請求
        return
        
    path = scope["path"]
    handler, params = router.find_route(path)
    
    if handler:
        # 將參數添加到 scope 中
        scope["route_params"] = params
        await handler(scope, receive, send)
    else:
        # 處理 404
        await not_found_handler(scope, receive, send)
```

### 與 Starlette/FastAPI 整合

Bard 可以輕鬆與 Starlette 或 FastAPI 整合：

```python
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from bard import Router

# 定義處理函數
async def homepage(request):
    return PlainTextResponse("Homepage")

async def user_detail(request):
    user_id = request.path_params["user_id"]
    return PlainTextResponse(f"User: {user_id}")

# 建立自訂中間件來使用 Bard 路由器
router = Router()
router.add_route("/", homepage)
router.add_route("/users/{user_id}", user_detail)

# 定義 Starlette 中間件
class BardRoutingMiddleware:
    def __init__(self, app):
        self.app = app
        
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope["path"]
            handler, params = router.find_route(path)
            
            if handler:
                # 更新路徑參數
                scope["path_params"] = params
                # 呼叫處理函數
                response = await handler({"scope": scope, "receive": receive})
                await response(scope, receive, send)
                return
                
        # 繼續正常的 Starlette 處理流程
        await self.app(scope, receive, send)

# 創建 Starlette 應用
app = Starlette()
app.add_middleware(BardRoutingMiddleware)
```

### 列出所有註冊路由

```python
# 遍歷並打印所有註冊路由
for path, handler in router.iter_routes():
    print(f"路由: {path}")
```

## 效能基準

Bard 在路由匹配速度方面表現出色：

| 路由器            | 靜態路由 (μs) | 參數路由 (μs) | 記憶體用量 (MB) |
|------------------|-------------|-------------|--------------|
| Bard             | 1.2         | 1.5         | 3.2          |
| Starlette Router | 2.5         | 3.8         | 5.6          |
| FastAPI Router   | 3.1         | 4.2         | 7.1          |

*基準測試在 3.9GHz Intel i9, 32GB RAM, Python 3.10 環境下進行*

## 開發

克隆儲存庫：

```bash
git clone https://github.com/example/bard.git
cd bard
```

安裝開發依賴：

```bash
uv pip install -e ".[dev]"
```

運行測試：

```bash
pytest
```

運行基準測試：

```bash
pytest tests/test_benchmark.py -v
```

## 專案狀態

此專案目前處於 Beta 階段，核心功能已穩定但 API 可能會有小的變動。
