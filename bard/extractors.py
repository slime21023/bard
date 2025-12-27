class _Extractor:
    __slots__ = ("name",)

    def __init__(self, name: str | None = None):
        self.name = name

    def __repr__(self) -> str:
        name = f" name={self.name!r}" if self.name else ""
        return f"{self.__class__.__name__}({name})"


class Json(_Extractor):
    __slots__ = ()

    def __init__(self) -> None:
        super().__init__(None)


class Path(_Extractor):
    __slots__ = ()


class Query(_Extractor):
    __slots__ = ()


class Header(_Extractor):
    __slots__ = ()


class State(_Extractor):
    __slots__ = ()


class Form(_Extractor):
    __slots__ = ()


class File(_Extractor):
    __slots__ = ()


def normalize_extractor(meta: object) -> _Extractor | None:
    if isinstance(meta, _Extractor):
        return meta
    if isinstance(meta, type) and issubclass(meta, _Extractor):
        return meta()
    return None
