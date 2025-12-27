# Conversion Rules

This page describes the conversion behavior used by extractors (query/path/header/form) and by DI fallbacks.

## Missing Values

- If a parameter has a Python default, the default is used.
- If the annotation is `Optional[T]` / `T | None`, `None` is used.
- Otherwise Bard returns 422 for missing extractor values.

## Booleans

Booleans accept: `true/false/1/0/yes/no/on/off` (case-insensitive).

## Lists

- Query and form fields may repeat (`?tag=a&tag=b`).
- Annotate as `list[T]` to receive a list.

## Union Conversion

For `Union[...]` types, Bard tries each candidate in order and returns the first successful conversion.

## DI: "Missing Provider" vs "Missing Extractor"

If a parameter has no extractor:

- `Depends(...)` resolves via the provider.
- Otherwise Bard attempts type-based DI.

If there is no provider:

- For "request-like" data types (for example `int`, `str`, `list[str]`), Bard treats it as a missing extractor error.
- For other types, Bard treats it as a missing provider error.
