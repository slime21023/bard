from __future__ import annotations

from typing import Annotated

from bard import BardApp, File, Form, FormData, Router, TestClient, UploadFile


def _multipart_body(boundary: str, fields: dict[str, str], files: dict[str, tuple[str, bytes, str]]) -> bytes:
    lines: list[bytes] = []
    for name, value in fields.items():
        lines.append(f"--{boundary}\r\n".encode("latin-1"))
        lines.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("latin-1"))
        lines.append(value.encode("utf-8"))
        lines.append(b"\r\n")
    for name, (filename, content, content_type) in files.items():
        lines.append(f"--{boundary}\r\n".encode("latin-1"))
        lines.append(
            f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode("latin-1")
        )
        lines.append(f"Content-Type: {content_type}\r\n\r\n".encode("latin-1"))
        lines.append(content)
        lines.append(b"\r\n")
    lines.append(f"--{boundary}--\r\n".encode("latin-1"))
    return b"".join(lines)


def test_form_urlencoded_field():
    async def handler(name: Annotated[str, Form]):
        return {"name": name}

    router = Router()
    router.post("/submit", handler)
    app = BardApp(router)

    body = b"name=alice"
    headers = {"content-type": "application/x-www-form-urlencoded"}

    with TestClient(app) as client:
        resp = client.request("POST", "/submit", body=body, headers=headers)

    assert resp.json()["name"] == "alice"


def test_form_urlencoded_list():
    async def handler(tags: Annotated[list[str], Form("tag")]):
        return {"tags": tags}

    router = Router()
    router.post("/submit", handler)
    app = BardApp(router)

    body = b"tag=a&tag=b"
    headers = {"content-type": "application/x-www-form-urlencoded"}

    with TestClient(app) as client:
        resp = client.request("POST", "/submit", body=body, headers=headers)

    assert resp.json()["tags"] == ["a", "b"]


def test_formdata_extractor():
    async def handler(form: Annotated[FormData, Form]):
        return {"fields": form.fields, "files": list(form.files.keys())}

    router = Router()
    router.post("/submit", handler)
    app = BardApp(router)

    body = b"name=alice&age=30"
    headers = {"content-type": "application/x-www-form-urlencoded"}

    with TestClient(app) as client:
        resp = client.request("POST", "/submit", body=body, headers=headers)

    assert resp.json()["fields"]["name"] == ["alice"]
    assert resp.json()["fields"]["age"] == ["30"]
    assert resp.json()["files"] == []


def test_formdata_dict_extractor():
    async def handler(form: Annotated[dict, Form]):
        return {"form": form}

    router = Router()
    router.post("/submit", handler)
    app = BardApp(router)

    body = b"name=alice&tag=a&tag=b"
    headers = {"content-type": "application/x-www-form-urlencoded"}

    with TestClient(app) as client:
        resp = client.request("POST", "/submit", body=body, headers=headers)

    assert resp.json()["form"]["name"] == "alice"
    assert resp.json()["form"]["tag"] == ["a", "b"]


def test_multipart_field_and_file():
    async def handler(name: Annotated[str, Form], upload: Annotated[UploadFile, File("file")]):
        return {"name": name, "filename": upload.filename, "content": upload.text()}

    router = Router()
    router.post("/upload", handler)
    app = BardApp(router)

    boundary = "boundary123"
    body = _multipart_body(
        boundary,
        fields={"name": "alice"},
        files={"file": ("hello.txt", b"hello", "text/plain")},
    )
    headers = {"content-type": f"multipart/form-data; boundary={boundary}"}

    with TestClient(app) as client:
        resp = client.request("POST", "/upload", body=body, headers=headers)

    data = resp.json()
    assert data["name"] == "alice"
    assert data["filename"] == "hello.txt"
    assert data["content"] == "hello"


def test_multipart_file_bytes():
    async def handler(upload: Annotated[bytes, File("file")]):
        return {"size": len(upload)}

    router = Router()
    router.post("/upload", handler)
    app = BardApp(router)

    boundary = "boundary123"
    body = _multipart_body(
        boundary,
        fields={},
        files={"file": ("hello.txt", b"hello", "text/plain")},
    )
    headers = {"content-type": f"multipart/form-data; boundary={boundary}"}

    with TestClient(app) as client:
        resp = client.request("POST", "/upload", body=body, headers=headers)

    assert resp.json()["size"] == 5


def test_multipart_file_list():
    async def handler(files: Annotated[list[UploadFile], File("file")]):
        return {"count": len(files)}

    router = Router()
    router.post("/upload", handler)
    app = BardApp(router)

    boundary = "boundary123"
    body = _multipart_body(
        boundary,
        fields={},
        files={
            "file": ("a.txt", b"a", "text/plain"),
        },
    ).replace(f"--{boundary}--\r\n".encode("latin-1"), b"")
    body += _multipart_body(
        boundary,
        fields={},
        files={
            "file": ("b.txt", b"b", "text/plain"),
        },
    )
    headers = {"content-type": f"multipart/form-data; boundary={boundary}"}

    with TestClient(app) as client:
        resp = client.request("POST", "/upload", body=body, headers=headers)

    assert resp.json()["count"] == 2


def test_missing_form_field_returns_422():
    async def handler(name: Annotated[str, Form("name")]):
        return {"name": name}

    router = Router()
    router.post("/submit", handler)
    app = BardApp(router)

    body = b"other=1"
    headers = {"content-type": "application/x-www-form-urlencoded"}

    with TestClient(app) as client:
        resp = client.request("POST", "/submit", body=body, headers=headers)

    assert resp.status == 422
    assert "Missing required value" in resp.json()["detail"]


def test_missing_file_returns_422():
    async def handler(upload: Annotated[UploadFile, File("file")]):
        return {"name": upload.filename}

    router = Router()
    router.post("/upload", handler)
    app = BardApp(router)

    boundary = "boundary123"
    body = _multipart_body(boundary, fields={"name": "alice"}, files={})
    headers = {"content-type": f"multipart/form-data; boundary={boundary}"}

    with TestClient(app) as client:
        resp = client.request("POST", "/upload", body=body, headers=headers)

    assert resp.status == 422
    assert "Missing required value" in resp.json()["detail"]


def test_missing_boundary_returns_400():
    async def handler(name: Annotated[str, Form("name")]):
        return {"name": name}

    router = Router()
    router.post("/submit", handler)
    app = BardApp(router)

    body = b""
    headers = {"content-type": "multipart/form-data"}

    with TestClient(app) as client:
        resp = client.request("POST", "/submit", body=body, headers=headers)

    assert resp.status == 400
    assert resp.json()["detail"] == "Invalid form data"


def test_form_unknown_content_type_returns_empty():
    async def handler(form: Annotated[FormData, Form]):
        return {"fields": form.fields}

    router = Router()
    router.post("/submit", handler)
    app = BardApp(router)

    body = b"ignored"
    headers = {"content-type": "text/plain"}

    with TestClient(app) as client:
        resp = client.request("POST", "/submit", body=body, headers=headers)

    assert resp.json()["fields"] == {}


def test_file_invalid_target_type_returns_422():
    async def handler(upload: Annotated[int, File("file")]):
        return {"size": upload}

    router = Router()
    router.post("/upload", handler)
    app = BardApp(router)

    boundary = "boundary123"
    body = _multipart_body(
        boundary,
        fields={},
        files={"file": ("hello.txt", b"hello", "text/plain")},
    )
    headers = {"content-type": f"multipart/form-data; boundary={boundary}"}

    with TestClient(app) as client:
        resp = client.request("POST", "/upload", body=body, headers=headers)

    assert resp.status == 422
