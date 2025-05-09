#!/usr/bin/env python
# cython: language_level=3
"""
Cython ASGI Trie Router
一個高效能的 ASGI 路由器，基於 Trie 樹結構，用於路徑匹配和參數提取。
"""

# 類型定義
ctypedef object _ASGIApp     # ASGI 應用程式 (Python callable)
ctypedef dict _RouteParams   # 路由參數字典 {param_name: value}

cdef class _TrieNode:
    """
    Trie 樹節點，用於儲存路由資訊和實現路徑匹配
    """
    # 類別常數，用於在 children 字典中表示參數節點的特殊鍵
    PARAM_KEY = "<param>"
    
    cdef dict children      # 子節點字典
    cdef _ASGIApp asgi_app  # ASGI 應用程式
    cdef bint is_path_end   # 是否為路徑終點
    cdef str param_name     # 參數名稱
    
    def __cinit__(self):
        """初始化一個新的 Trie 節點"""
        self.children = {}
        self.asgi_app = None
        self.is_path_end = False
        self.param_name = None


cdef class CythonASGITrieRouter:
    """
    Cython ASGI Trie Router - 高效能的 ASGI 路由器
    使用 Trie 樹結構實現快速的路徑匹配和參數提取
    """
    cdef _TrieNode root_node
    
    def __cinit__(self):
        """初始化路由器"""
        self.root_node = _TrieNode()
    
    cdef list _normalize_path(self, str path):
        """
        標準化路徑字串，轉換為段列表
        
        Args:
            path: 原始路徑字串，例如 "/users/{id}"
            
        Returns:
            路徑段列表，例如 ["users", "{id}"]
        """
        if not path:  # 處理空字串路徑
            return []
        if path == "/":  # 根路徑
            return []
        
        # 去除開頭和結尾的斜線，然後分割
        normalized = path.strip("/")
        if not normalized:  # 路徑是類似 "//" 的情形
            return []  # 視為根路徑
        return normalized.split('/')
    
    cpdef void add_route(self, str path, _ASGIApp app_to_serve):
        """
        註冊一個新的路由路徑及其處理應用程式
        
        Args:
            path: 路由路徑，例如 "/users/{id}"
            app_to_serve: 處理此路徑的 ASGI 應用程式
        """
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
    
    cpdef tuple find_route(self, str path):
        """
        查找匹配給定路徑的路由
        
        Args:
            path: 請求路徑，例如 "/users/123"
            
        Returns:
            Tuple of (ASGI app, params dict) 或 (None, None) 如果沒有找到
        """
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
    
    cdef _iter_routes_recursive(self, _TrieNode node, list current_path_parts, list routes_found):
        """遞迴輔助方法，用於遍歷路由"""
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
    
    def iter_routes(self):
        """產生一個包含所有已註冊路由的迭代器"""
        cdef list routes_found = []
        self._iter_routes_recursive(self.root_node, [], routes_found)
        for route_path, app in routes_found:
            yield (route_path, app)
