#!/usr/bin/env python3
"""
設置腳本：用於編譯和安裝 Bard ASGI Trie Router
"""

from setuptools import setup, Extension
from Cython.Build import cythonize

extensions = [
    Extension(
        "bard.router",
        ["bard/router.pyx"],
        extra_compile_args=["-O3"]  # 最高級別優化
    )
]

setup(
    name="bard",
    version="0.0.1",
    description="Bard ASGI Trie Router - 高效能的 ASGI 路由器",
    author="Bard ASGI Team",
    author_email="example@example.com",
    url="https://github.com/example/bard",
    packages=["bard"],
    ext_modules=cythonize(
        extensions,
        compiler_directives={'language_level': "3"}
    ),
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    zip_safe=False,  # Cython 模塊不能為 zip 安全
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-benchmark>=3.4.0",
            "pytest-cov>=3.0.0",
        ],
    },
)
