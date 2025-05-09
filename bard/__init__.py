"""
Cython ASGI Trie Router
一個高效能的 ASGI 路由器，使用 Trie 樹實現，支援靜態和參數化路徑。
"""

from .router import CythonASGITrieRouter as Router

__version__ = "0.0.1"
__all__ = ["Router"]
