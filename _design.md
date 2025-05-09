# Bard - Cython ASGI Trie Router 軟體設計文件

**版本**: 0.0.1  
**日期**: 2025年5月9日  
**狀態**: 設計草案

## 目錄
- [1. 導論](#1-導論)
- [2. 系統概觀](#2-系統概觀)
- [3. 架構設計](#3-架構設計)
- [4. 詳細設計](#4-詳細設計)
- [5. 實作考量](#5-實作考量)
- [6. 部署與編譯](#6-部署與編譯)
- [7. 測試策略](#7-測試策略)
- [8. 附錄](#8-附錄)

---

## 1. 導論

### 1.1 目的
本文件詳細描述一個完全以 Cython 實現的高效能 Trie Tree 路由器，專為 ASGI (Asynchronous Server Gateway Interface) 應用程式設計。此路由器旨在提供快速的路徑匹配功能，並將請求分派給相應的 ASGI 應用程式。

### 1.2 範圍
本設計涵蓋以下功能：
* 基於 Trie Tree 的路徑註冊與查找
* 支援靜態路徑段和參數化路徑段 (例如 `/users/{id}`)
* 從請求路徑中提取參數
* 提供介面來遍歷所有已註冊的路由及其對應的 ASGI 應用程式
* 當找不到匹配路徑時，返回明確的未找到指示
* 設計上不直接處理多執行緒同步問題，假設在單一事件迴圈或由外部機制處理同步

### 1.3 定義、首字母縮寫詞和縮略語
| 術語 | 定義 |
|------|------|
| **ASGI** | Asynchronous Server Gateway Interface，Python 非同步 Web 應用程式的標準介面 |
| **Trie Tree** | 前綴樹或字典樹，一種用於高效字串檢索的樹狀資料結構 |
| **SDD** | Software Design Document (軟體設計文件) |
| **Cython** | 一種程式語言，允許為 Python 編寫 C 擴展，旨在提高效能 |
| **ASGI App** | 符合 ASGI 規範的可呼叫物件，用於處理 HTTP 請求 |
| **Route Parameters** | 從路徑中動態提取的值，例如 `/users/123` 中的 `123` |

---

## 2. 系統概觀

### 2.1 產品視角
Cython ASGI Trie Router 是一個核心路由組件，可被整合到 ASGI Web 框架或作為 ASGI 中間件的一部分使用。它接收請求路徑，高效地查找已註冊的路由，並確定應處理該請求的 ASGI 應用程式及提取的路徑參數。

```
┌──────────────┐     ┌─────────────────────┐     ┌───────────────┐
│ HTTP Request │────▶│ Cython ASGI Router  │────▶│ ASGI Handler  │
└──────────────┘     │  1. 路徑匹配        │     └───────────────┘
                     │  2. 參數提取        │
                     │  3. 應用程式選擇    │
                     └─────────────────────┘
```

### 2.2 設計目標
* **高效能**: 利用 Cython 的靜態型別和 C 級別的資料結構，最大限度地減少路徑查找的延遲
* **功能完整性**: 支援常見的路由需求，包括靜態路徑、參數化路徑和參數提取
* **易於整合**: 提供清晰的 Cython/Python API，方便 ASGI 框架或中間件使用
* **可維護性**: 儘管使用 Cython，但仍力求程式碼結構清晰，易於理解和維護

### 2.3 使用場景

#### 2.3.1 基本路由註冊與查找
```python
# 建立路由器實例
router = Router()

# 註冊路由
router.add_route("/", index_app)
router.add_route("/users", users_list_app)
router.add_route("/users/{user_id}", user_detail_app)

# 查找路由
app, params = router.find_route("/users/123")
# 結果: app = user_detail_app, params = {"user_id": "123"}
```

---

## 3. 架構設計

### 3.1 組件概觀
系統主要由以下 Cython 類別組成：

```
┌───────────────────────┐
│ CythonASGITrieRouter  │
├───────────────────────┤
│ - root_node: _TrieNode│
│ + add_route()         │
│ + find_route()        │
│ + iter_routes()       │
└───────┬───────────────┘
        │
        │ 包含
        ▼
┌───────────────────────┐
│ _TrieNode             │
├───────────────────────┤
│ - children: dict      │
│ - asgi_app: _ASGIApp  │
│ - is_path_end: bool   │
│ - param_name: str     │
└───────────────────────┘
```

### 3.2 資料結構設計

#### 3.2.1 類型定義
```cython
# 類型別名
ctypedef object _ASGIApp     # ASGI 應用程式 (Python callable)
ctypedef dict _RouteParams   # 路由參數字典 {param_name: value}
```

#### 3.2.2 `_TrieNode` 類別
`_TrieNode` 代表 Trie 樹中的一個節點，是路由器的基本構建塊。

**屬性**:
* `dict children`: 子節點字典，鍵為下一個路徑段或參數標記，值為 `_TrieNode` 實例
* `_ASGIApp asgi_app`: 如果這是路徑終點，則存儲對應的 ASGI 應用程式
* `bint is_path_end`: 標記該節點是否為一個完整註冊路徑的終點
* `str param_name`: 如果此節點表示參數段，則存儲參數名稱

**常數**:
* `PARAM_KEY = "<param>"`: 用於在 `children` 字典中標識參數節點的特殊鍵

**節點類型**:
1. **靜態節點**: 對應固定路徑段，如 `/users` 中的 "users"
2. **參數節點**: 對應動態路徑段，如 `/users/{id}` 中的 "{id}"
3. **終點節點**: 標記一個完整路徑的結束，包含 ASGI 應用程式

#### 3.2.3 Trie 樹結構示例
以下 ASCII 圖表展示了註冊 `/users` 和 `/users/{id}` 後形成的 Trie 樹結構：

```
               ┌────────┐
               │ root   │
               └────┬───┘
                    │
                    ▼
               ┌────────┐
          ┌───▶│"users" │
          │    └────┬───┘
          │         │
┌─────────┴────┐    ▼
│ app: users_  │◀──┐    ┌────────────┐
│ list_app     │   └───▶│ "<param>"  │
└──────────────┘        │ name: "id" │
                        └─────┬──────┘
                              │
                        ┌─────▼──────┐
                        │ app: user_ │
                        │ detail_app │
                        └────────────┘
```

### 3.3 介面設計

#### 3.3.1 `CythonASGITrieRouter` 公開 API

```cython
cdef class CythonASGITrieRouter:
    # 註冊一個新的路由
    cpdef void add_route(self, str path, _ASGIApp app_to_serve)
    
    # 根據路徑查找匹配的路由
    cpdef tuple find_route(self, str path)
    
    # 遍歷所有已註冊的路由
    def iter_routes(self)
```

#### 3.3.2 API 詳細說明

**`add_route(path, app_to_serve)`**
* **功能**: 註冊新的路由路徑及其處理應用程式
* **參數**:
  * `path (str)`: 路由路徑，例如 `/users/{id}`
  * `app_to_serve (_ASGIApp)`: 處理此路徑的 ASGI 應用程式
* **返回**: `void`
* **可能的異常**:
  * 當發生參數命名衝突時可能拋出 `ValueError`（目前設計中被註釋掉）

**`find_route(path)`**
* **功能**: 查找匹配給定路徑的路由
* **參數**:
  * `path (str)`: 請求路徑，例如 `/users/123`
* **返回**: `tuple(_ASGIApp, _RouteParams)`
  * 成功時: `(匹配的ASGI應用程式, 參數字典)`
  * 失敗時: `(None, None)`

**`iter_routes()`**
* **功能**: 產生一個包含所有已註冊路由的迭代器
* **返回**: 產生元組 `(路徑字串, ASGI應用程式)`

---

## 4. 詳細設計

### 4.1 `_TrieNode` 類別實作

```cython
cdef class _TrieNode:
    # 類別常數
    PARAM_KEY = "<param>"
    
    def __cinit__(self):
        self.children = {}
        self.asgi_app = None
        self.is_path_end = False
        self.param_name = None
```

### 4.2 `CythonASGITrieRouter` 類別實作

#### 4.2.1 初始化

```cython
cdef class CythonASGITrieRouter:
    def __cinit__(self):
        self.root_node = _TrieNode()
```

#### 4.2.2 路徑正規化

```cython
cdef list _normalize_path(self, str path):
    if not path:  # 處理空字串路徑
        return []
    if path == "/":  # 根路徑
        return []
    
    # 去除開頭和結尾的斜線，然後分割
    normalized = path.strip("/")
    if not normalized:  # 路徑是類似 "//" 的情形
        return []  # 視為根路徑
    return normalized.split('/')
```

#### 4.2.3 新增路由

```cython
cpdef void add_route(self, str path, _ASGIApp app_to_serve):
    cdef list segments = self._normalize_path(path)
    cdef _TrieNode current_node = self.root_node
    cdef str segment
    cdef str param_name_extracted
    cdef _TrieNode child_node  # 用於保存遍歷/創建過程中的下一個節點

    for segment in segments:
        # 處理參數段 (如 "{id}")
        if segment.startswith('{') and segment.endswith('}') and len(segment) > 2:
            param_name_extracted = segment[1:-1]
            
            # 檢查參數節點是否已存在
            if _TrieNode.PARAM_KEY not in current_node.children:
                child_node = _TrieNode()
                child_node.param_name = param_name_extracted
                current_node.children[_TrieNode.PARAM_KEY] = child_node
            # 可選的參數命名衝突處理 (目前被註釋)
            # 
            # else:
            #   如果參數節點已存在，確保參數名稱一致
            #   或決定衝突解決策略 (例如: 錯誤、覆寫、允許多個)
            #   在此設計中，我們假設該路徑層級的第一個註冊參數名稱有效
            #   if current_node.children[_TrieNode.PARAM_KEY].param_name != param_name_extracted:
            #       raise ValueError(f"Conflicting parameter names: {current_node.children[_TrieNode.PARAM_KEY].param_name} vs {param_name_extracted}")
            
            current_node = current_node.children[_TrieNode.PARAM_KEY]
            
            # 如果節點的參數名尚未設置，則設置它
            if not current_node.param_name:
                current_node.param_name = param_name_extracted
        
        # 處理靜態段 (如 "users")
        else:
            if segment not in current_node.children:
                current_node.children[segment] = _TrieNode()
            current_node = current_node.children[segment]
    
    # 標記路徑終點並關聯 ASGI 應用程式
    current_node.is_path_end = True
    current_node.asgi_app = app_to_serve
```

#### 4.2.4 查找路由

```cython
cpdef tuple find_route(self, str path):
    cdef list segments = self._normalize_path(path)
    cdef _RouteParams extracted_params = {}
    cdef _TrieNode current_node = self.root_node
    cdef str segment
    cdef _TrieNode param_node_candidate  # 用於保存可能的參數節點

    for segment in segments:
        # 優先嘗試靜態匹配
        if segment in current_node.children:
            current_node = current_node.children[segment]
        # 其次嘗試參數匹配
        elif _TrieNode.PARAM_KEY in current_node.children:
            param_node_candidate = current_node.children[_TrieNode.PARAM_KEY]
            if param_node_candidate.param_name:  # 確保參數名已設置
                extracted_params[param_node_candidate.param_name] = segment
            else:
                # 此情況理論上不應發生，如果 add_route 正確設置 param_name
                return (None, None)  # 或拋出內部錯誤
            current_node = param_node_candidate
        else:  # 沒有匹配此段
            return (None, None)
    
    # 檢查是否到達路徑終點
    if current_node.is_path_end:
        return (current_node.asgi_app, extracted_params)
    else:  # 路徑是已註冊路由的前綴，但自身不是路由
        return (None, None)
```

#### 4.2.5 遍歷所有路由

```cython
def iter_routes(self):
    """遍歷所有已註冊的路由及其處理應用程式"""
    cdef list routes_found = []
    self._iter_routes_recursive(self.root_node, [], routes_found)
    for route_path, app in routes_found:
        yield (route_path, app)

cdef _iter_routes_recursive(self, _TrieNode node, list current_path_parts, list routes_found):
    # 如果節點是路徑終點，將其添加到結果中
    if node.is_path_end:
        # 將路徑部分合併為字串
        path_str = "/" if not current_path_parts else "/" + "/".join(current_path_parts)
        routes_found.append((path_str, node.asgi_app))
    
    # 遞迴處理所有子節點
    for segment, child_node in node.children.items():
        if segment == _TrieNode.PARAM_KEY:
            # 參數節點，用花括號包裹參數名
            param_segment = "{" + child_node.param_name + "}"
            self._iter_routes_recursive(
                child_node,
                current_path_parts + [param_segment],
                routes_found
            )
        else:
            # 靜態節點
            self._iter_routes_recursive(
                child_node,
                current_path_parts + [segment],
                routes_found
            )
```

---

## 5. 實作考量

### 5.1 效能優化

1. **靜態優先匹配**: 在路由查找中，優先嘗試靜態段匹配以避免不必要的參數處理。
2. **路徑正規化快取**: 對於頻繁使用的路徑，可考慮快取正規化結果。
3. **記憶體最佳化**: 使用 Cython 的靜態類型和 C 數據結構減少記憶體占用。

### 5.2 可能的改進

1. **通配符支援**: 增加 `*` 或 `**` 通配符支援，用於匹配多個路徑段。
2. **正則表達式參數**: 為參數增加規則驗證，例如 `{id:[0-9]+}`。
3. **多重路由衝突解決**: 提供更健全的策略處理同路徑不同參數名的情況。
4. **並發安全**: 增加線程安全保證，以支援多線程環境。

### 5.3 潛在限制

1. **參數命名衝突**: 目前的設計在存在命名衝突時依賴首次註冊的名稱，可能導致混淆。
2. **非並發安全**: 目前設計假設單一事件迴圈或外部同步機制。
3. **路徑限制**: 不支援非路徑部分的匹配（如查詢參數、HTTP 方法）。

---

## 6. 部署與編譯

### 6.1 編譯指南

#### 6.1.1 設置 Cython 環境

```bash
pip install cython
```

#### 6.1.2 `setup.py` 檔案

```python
from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [
    Extension(
        "cython_asgi_router",
        ["router.pyx"],
        extra_compile_args=["-O3"]  # 最高級別優化
    )
]

setup(
    name="cython_asgi_router",
    ext_modules=cythonize(extensions),
    zip_safe=False
)
```

#### 6.1.3 編譯命令

```bash
python setup.py build_ext --inplace
```

### 6.2 使用範例

```python
from cython_asgi_router import CythonASGITrieRouter

# 建立路由器
router = CythonASGITrieRouter()

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

# 註冊路由
router.add_route("/", index)

# 以中間件形式使用路由器
async def router_middleware(scope, receive, send):
    if scope["type"] != "http":
        return
        
    path = scope["path"]
    app, params = router.find_route(path)
    
    if app:
        # 將參數添加到 scope 中
        scope["route_params"] = params
        await app(scope, receive, send)
    else:
        # 處理 404
        await send({
            'type': 'http.response.start',
            'status': 404
        })
        await send({
            'type': 'http.response.body',
            'body': b'Not Found'
        })
```

---

## 7. 測試策略

### 7.1 單元測試

1. **路徑正規化測試**: 測試各種路徑輸入的正規化結果。
2. **路由註冊測試**: 驗證路由正確註冊到 Trie 中。
3. **路徑查找測試**: 確保能正確查找靜態和參數化路徑。
4. **參數提取測試**: 驗證從路徑中正確提取參數。
5. **邊界情況測試**: 測試空路徑、根路徑、重複斜線等特殊情況。

### 7.2 效能測試

1. **基準測試**: 與純 Python 實現和其他路由器比較。
2. **壓力測試**: 在大量路由和高頻率查詢下的性能。
3. **記憶體使用測試**: 監測不同數量路由下的記憶體佔用。

---

## 8. 附錄

### 8.1 參考資料

1. ASGI 規範: [ASGI Specification](https://asgi.readthedocs.io/en/latest/specs/index.html)
2. Cython 文檔: [Cython Documentation](https://cython.readthedocs.io/)
3. Trie 資料結構: [Wikipedia - Trie](https://en.wikipedia.org/wiki/Trie)

### 8.2 修訂歷史

| 版本  | 日期 | 描述 | 作者 |
|-------|------|------|------|
| 0.0.1 | 2025-05-09 | 初始設計文件草案 | - |