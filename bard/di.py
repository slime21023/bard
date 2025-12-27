from __future__ import annotations

import inspect
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any, Callable


ProviderCallable = Callable[..., Any]


@dataclass(frozen=True, slots=True)
class ProviderSpec:
    provider: ProviderCallable
    use_cache: bool = True
    localns: dict[str, Any] | None = None


class Depends:
    __slots__ = ("provider", "use_cache")

    def __init__(self, provider: ProviderCallable, *, use_cache: bool = True) -> None:
        self.provider = provider
        self.use_cache = use_cache

    def __repr__(self) -> str:
        return f"Depends(provider={self.provider}, use_cache={self.use_cache})"


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[object, ProviderSpec] = {}

    def provide(
        self,
        key: object,
        provider: ProviderCallable,
        *,
        use_cache: bool = True,
        localns: dict[str, Any] | None = None,
    ) -> None:
        if key in self._providers:
            raise ValueError(f"Provider already registered for {key!r}")
        self._providers[key] = ProviderSpec(provider=provider, use_cache=use_cache, localns=localns)

    def get(self, key: object) -> ProviderSpec | None:
        return self._providers.get(key)

    def items(self):
        return self._providers.items()


async def enter_resource(stack: AsyncExitStack | None, value: Any) -> Any:
    if stack is None:
        return value
    if hasattr(value, "__aenter__") and hasattr(value, "__aexit__"):
        return await stack.enter_async_context(value)  # type: ignore[arg-type]
    if hasattr(value, "__enter__") and hasattr(value, "__exit__"):
        return stack.enter_context(value)  # type: ignore[arg-type]
    aclose = getattr(value, "aclose", None)
    if callable(aclose):
        if inspect.iscoroutinefunction(aclose):
            stack.push_async_callback(aclose)  # type: ignore[arg-type]
        else:
            async def _awaitable_close() -> None:
                result = aclose()
                if inspect.isawaitable(result):
                    await result

            stack.push_async_callback(_awaitable_close)
        return value
    close = getattr(value, "close", None)
    if callable(close):
        stack.callback(close)
    return value
