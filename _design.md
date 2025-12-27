# Bard 技術文件

**Bard** 是一個基於 Python 3.10+ 的下一代 ASGI 底層開發框架。

它的設計靈感源自 Rust 的 **Axum**，旨在透過 **Type-Driven（類型驅動）** 開發模式、**Radix Tree 路由** 以及 **啟動時編譯（Startup-time Compilation）** 技術，提供比 Starlette 更優異的開發體驗與執行效能。

---

## 核心特性 (Key Features)

- **Axum-like 設計哲學**：告別手動解析 Request。透過 Type Hints 宣告需求，框架自動注入。
- **O(K) 高效路由**：採用 **Radix Tree** 演算法取代傳統的線性 Regex 掃描，路由匹配速度與路由數量無關。
- **極速 JSON 處理**：核心整合 **msgspec**，提供比 Pydantic 快 10-50 倍的序列化與驗證效能。
- **啟動時編譯**：在伺服器啟動瞬間分析 Handler 依賴，消除 Runtime 的反射（Reflection）開銷。
- **ASGI 原生**：完全兼容 ASGI 3.0 標準，可運行於 Uvicorn, Hypercorn 等伺服器。

---

## 1. 安裝 (Installation)

Bard 是一個輕量級框架。

```bash
# 假設 Bard 已發布
pip install bard-web uvicorn msgspec
```

---

## 2. 快速上手 (Quick Start)

建立一個 `main.py`：

```python
import uvicorn
from bard import BardApp, Router, Json
from typing import Annotated
import msgspec

# 1. 定義資料結構 (推薦使用 msgspec.Struct 以獲得極致效能)
class CreateUser(msgspec.Struct):
    username: str
    email: str

# 2. 定義 Handler
# 使用 Annotated 宣告依賴，Bard 會自動提取並驗證
async def create_user(payload: Annotated[CreateUser, Json]):
    return {
        "status": "success",
        "user": payload.username,
        "email": payload.email
    }, 201

async def root():
    return "Hello from Bard!"

# 3. 註冊路由
router = Router()
router.get("/", root)
router.post("/users", create_user)

# 4. 啟動應用
app = BardApp(router)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
```

---

## 3. 核心概念：提取器 (Extractors)

Bard 的核心在於 **Extractors**。你不需要在函數內寫 `request.json()` 或 `request.query_params`。你只需要在參數簽名中「宣告」你需要什麼。

### 內建提取器

| 提取器 | 類型標註範例 | 功能說明 |
| :--- | :--- | :--- |
| **Json** | `Annotated[T, Json]` | 解析 Body。支援 `msgspec.Struct`, `dataclass`, `Pydantic`, `dict`。 |
| **Path** | `Annotated[str, Path]` | 提取 URL 路徑參數 (如 `/users/{id}`)。 |
| **Query** | `Annotated[str, Query]` | 提取 URL 查詢參數。 |
| **Header** | `Annotated[str, Header]` | 提取 HTTP Header 值。 |
| **State** | `Annotated[Any, State]` | 提取應用全域狀態 (如 DB 連線)。 |
| **Request** | `req: Request` | (Escape Hatch) 獲取原始 ASGI Request 物件。 |

### 複合使用範例

```python
async def search_users(
    query: Annotated[str, Query],
    version: Annotated[str, Header],
    db: Annotated[Database, State]
):
    # 這裡的代碼完全與 HTTP 協議解耦
    results = await db.search(query)
    return {"version": version, "data": results}
```

---

## 4. 路由系統 (Routing System)

Bard 使用 **Radix Tree** 進行路由匹配，這意味著無論你有 10 個還是 10,000 個路由，匹配速度都是恆定的 **O(K)** (K 為 URL 長度)。

相比之下，Starlette 使用線性掃描 (O(N))，路由越多越慢。

### 定義路由

```python
router = Router()

# 靜態路徑
router.get("/health", health_check)

# 路徑參數 (使用 {name} 語法)
router.get("/users/{user_id}", get_user)

# 支援多種 HTTP 方法
router.post("/items", create_item)
router.put("/items/{id}", update_item)
router.delete("/items/{id}", delete_item)
```

---

## 5. 資料驗證與效能 (Validation & Performance)

Bard 預設整合 **msgspec**，這是目前 Python 生態中最快的 JSON 庫。

### 推薦模式：msgspec.Struct

這是 Bard 效能最強的模式。解析、驗證、物件建立一次完成。

```python
import msgspec

class Item(msgspec.Struct):
    name: str
    price: float
    tags: list[str] = []

async def create_item(item: Annotated[Item, Json]):
    # 如果 JSON 缺少 name 或 price 格式錯誤
    # Bard 會直接回傳 422 Unprocessable Entity
    # Handler 根本不會被執行
    pass
```

### 相容模式：Pydantic & Dataclasses

Bard 也完全支援 Pydantic 模型和標準 dataclasses，方便現有專案遷移。

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str

async def update_user(user: Annotated[User, Json]):
    # 自動呼叫 User.model_validate_json()
    pass
```

---

## 6. 生命週期管理 (Lifespan)

Bard 支援 ASGI Lifespan 協議，用於處理應用啟動與關閉時的資源管理（如資料庫連線）。

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    # --- 啟動 ---
    print("Connecting to DB...")
    app.state["db"] = await Database.connect()
    
    yield
    
    # --- 關閉 ---
    print("Disconnecting...")
    await app.state["db"].close()

app = BardApp(router, lifespan=lifespan)
```

---

## 7. 測試 (Testing)

Bard 內建 `TestClient`，允許你在不啟動網路伺服器的情況下測試 API。

```python
from bard import TestClient

def test_create_user():
    client = TestClient(app)
    
    resp = client.request(
        "POST", 
        "/users", 
        body=b'{"username": "test", "email": "a@b.com"}'
    )
    
    assert resp.status == 201
    assert resp.json()["status"] == "success"
```

---

## 8. 進階架構：啟動時編譯 (Startup Compilation)

Bard 的高效能祕密在於 `CompiledHandler`。

1.  **分析階段**：當你呼叫 `BardApp(router)` 時，框架會遍歷所有 Handler。
2.  **編譯階段**：框架解析每個參數的 `Annotated` 類型，並建立一個優化的執行計畫（Execution Plan）。
3.  **執行階段**：當請求到達時，Bard 不需要再做任何反射（Reflection）或類型檢查，直接依照計畫執行提取器。

這使得 Bard 的 Runtime overhead 降至最低，接近手寫原始 ASGI 函數的效能。

---

## 9. 依賴注入與資源清理 (DI & Cleanup)

除了 `Annotated[..., Extractor]`，Bard 也支援 **按參數型別注入（type-based providers）**：

- 透過 `router.provide(Type, provider)` 註冊 provider，handler 直接宣告 `dep: Type` 即可注入。
- `Annotated[Type, Depends(provider)]` 可作為顯式覆寫（或參數化）的 escape hatch。
- provider 可以回傳：
  - 直接的物件 `T`
  - `contextmanager[T]` / `asynccontextmanager[T]`
  - 具有 `close()` / `aclose()` 的物件
- 框架會在每個 request/連線的生命週期邊界使用 `AsyncExitStack` 進行 LIFO 清理，避免錯誤路徑（例外、取消、斷線）漏清。

---

## 10. Middleware、WebSocket 與 Streaming

- **HTTP Middleware**：`app.add_middleware(middleware)`，middleware 以 `(request, call_next)` 形式包住 handler 執行，並可直接回傳任意 handler 結果型別（最後交由 response renderer 處理）。
- **WebSocket**：`router.websocket("/ws", handler)`，handler 透過 `WebSocket` 物件使用 `send_text/send_bytes/close` 等 API；路由匹配沿用同一套 radix tree。
- **Streaming**：支援 `StreamingResponse(AsyncIterable[bytes|str])`（或直接回傳 async iterable），由 ASGI `http.response.body` 多次送出。
