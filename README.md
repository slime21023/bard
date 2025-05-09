# Bard ASGI Trie Router

高效能的 ASGI 路由器，使用 Cython 實現，基於 Trie 樹結構設計，提供快速的路徑匹配和參數提取功能。

## 功能特點

- **高效能**：利用 Cython 的靜態型別和 C 級別效能
- **支援靜態和參數化路徑**：如 `/users` 和 `/users/{id}`
- **路徑參數提取**：自動從匹配的路由中提取參數值
- **路由優先級**：靜態路徑優先於參數化路徑
- **簡潔的 API**：易於整合到任何 ASGI 應用程式
- **無外部依賴**：僅依賴 Python 標準庫和 Cython

## 安裝 (TODO)

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

### 列出所有註冊路由

```python
# 遍歷並打印所有註冊路由
for path, handler in router.iter_routes():
    print(f"路由: {path}")
```

## 專案狀態

此專案目前處於 Beta 階段，核心功能已穩定但 API 可能會有小的變動。
