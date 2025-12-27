from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import parse_qs


@dataclass
class UploadFile:
    filename: str | None
    content_type: str | None
    content: bytes

    def text(self, encoding: str = "utf-8") -> str:
        return self.content.decode(encoding, errors="replace")


@dataclass
class FormData:
    fields: dict[str, list[str]] = field(default_factory=dict)
    files: dict[str, list[UploadFile]] = field(default_factory=dict)

    def get(self, name: str, default: Any | None = None) -> Any | None:
        values = self.fields.get(name)
        if not values:
            return default
        return values[0]

    def getlist(self, name: str) -> list[str]:
        return list(self.fields.get(name, []))

    def get_file(self, name: str) -> UploadFile | None:
        files = self.files.get(name)
        if not files:
            return None
        return files[0]


def parse_form(body: bytes, content_type: str) -> FormData:
    mime_type, params = _parse_content_type(content_type)
    if mime_type == "application/x-www-form-urlencoded":
        return _parse_urlencoded(body)
    if mime_type == "multipart/form-data":
        boundary = params.get("boundary")
        if not boundary:
            raise ValueError("Missing multipart boundary")
        return _parse_multipart(body, boundary.encode("latin-1"))
    return FormData()


def _parse_urlencoded(body: bytes) -> FormData:
    parsed = parse_qs(body.decode("latin-1"), keep_blank_values=True)
    return FormData(fields={key: list(values) for key, values in parsed.items()})


def _parse_multipart(body: bytes, boundary: bytes) -> FormData:
    form = FormData()
    marker = b"--" + boundary
    parts = body.split(marker)
    for part in parts:
        if not part or part == b"--\r\n" or part == b"--":
            continue
        part = part.lstrip(b"\r\n")
        if part.endswith(b"--"):
            part = part[:-2]
        part = part.rstrip(b"\r\n")
        if not part:
            continue
        header_blob, _, content = part.partition(b"\r\n\r\n")
        headers = _parse_headers(header_blob)
        disposition = headers.get("content-disposition", "")
        disp, disp_params = _parse_disposition(disposition)
        if disp != "form-data":
            continue
        name = disp_params.get("name")
        if not name:
            continue
        filename = disp_params.get("filename")
        if filename is not None:
            upload = UploadFile(
                filename=filename,
                content_type=headers.get("content-type"),
                content=content,
            )
            form.files.setdefault(name, []).append(upload)
        else:
            value = content.decode("utf-8", errors="replace")
            form.fields.setdefault(name, []).append(value)
    return form


def _parse_headers(blob: bytes) -> dict[str, str]:
    headers: dict[str, str] = {}
    for line in blob.split(b"\r\n"):
        if not line:
            continue
        key, _, value = line.partition(b":")
        headers[key.decode("latin-1").strip().lower()] = value.decode("latin-1").strip()
    return headers


def _parse_disposition(value: str) -> tuple[str, dict[str, str]]:
    parts = [part.strip() for part in value.split(";") if part.strip()]
    if not parts:
        return "", {}
    disposition = parts[0].lower()
    params: dict[str, str] = {}
    for part in parts[1:]:
        if "=" not in part:
            continue
        key, raw = part.split("=", 1)
        params[key.strip().lower()] = raw.strip().strip('"')
    return disposition, params


def _parse_content_type(value: str) -> tuple[str, dict[str, str]]:
    parts = [part.strip() for part in value.split(";") if part.strip()]
    if not parts:
        return "", {}
    mime_type = parts[0].lower()
    params: dict[str, str] = {}
    for part in parts[1:]:
        if "=" not in part:
            continue
        key, raw = part.split("=", 1)
        params[key.strip().lower()] = raw.strip().strip('"')
    return mime_type, params
