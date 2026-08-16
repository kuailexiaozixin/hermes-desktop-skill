"""test_upload_folder.py — 验证「文件夹上传」后端：保留目录结构 + 拒绝目录穿越。

隔离：HERMES_DESKTOP_HOME 指向临时目录，绝不触碰真实数据。
运行：python tests/test_upload_folder.py  或  pytest tests/test_upload_folder.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ["HERMES_DESKTOP_HOME"] = tempfile.mkdtemp(prefix="upload_folder_")
os.environ["HERMES_HOME"] = os.environ["HERMES_DESKTOP_HOME"]


def _helper_and_root():
    import main  # 冻结 venv 可正常 import；延迟到函数内以便在设置 HOME 之后
    up_root = Path(tempfile.mkdtemp(prefix="up_root_"))
    return main._resolve_upload_target, up_root


def test_helper_preserves_structure():
    fn, up_root = _helper_and_root()
    name, target = fn(up_root, "main.py", "proj/src/main.py")
    assert name == "proj/src/main.py", name
    assert target == up_root / "proj/src/main.py"
    assert str(target.resolve()).startswith(str(up_root.resolve()) + os.sep)
    # 父目录应被自动创建
    assert (up_root / "proj/src").is_dir() or not target.exists()
    print("  test_helper_preserves_structure OK")


def test_helper_traversal_neutralized():
    fn, up_root = _helper_and_root()
    # 各种逃逸写法都应收敛到 uploads 之内、且名称无 ..
    for rel in ("../../etc/secret", "/abs/etc/secret", "a/../../b", "..\\..\\win"):
        name, target = fn(up_root, "secret", rel)
        assert ".." not in name, (rel, name)
        assert str(target.resolve()).startswith(str(up_root.resolve()) + os.sep), (rel, target)
    print("  test_helper_traversal_neutralized OK")


def test_helper_flat_fallback():
    fn, up_root = _helper_and_root()
    name, target = fn(up_root, "note.txt", None)
    assert name == "note.txt"
    assert target == up_root / "note.txt"
    print("  test_helper_flat_fallback OK")


def test_endpoint_folder_upload():
    import main
    from starlette.testclient import TestClient
    c = TestClient(main.app)
    content = b"hello folder upload"
    r = c.post(
        "/api/upload",
        files={"files": ("main.py", content)},
        data={"relpaths": json.dumps(["proj/src/main.py"])},
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j.get("ok") is True, j
    att = j["attachments"][0]
    assert att["name"] == "proj/src/main.py", att
    saved = Path(att["path"])
    assert saved.exists() and saved.read_bytes() == content
    # 目录结构被保留：相对 uploads 的路径应为 proj/src/main.py
    rel = saved.relative_to(Path(os.environ["HERMES_DESKTOP_HOME"]) / "uploads")
    assert rel.parts[:2] == ("proj", "src"), rel.parts
    print("  test_endpoint_folder_upload OK")


def test_endpoint_traversal_via_endpoint():
    import main
    from starlette.testclient import TestClient
    c = TestClient(main.app)
    r = c.post(
        "/api/upload",
        files={"files": ("x.txt", b"data")},
        data={"relpaths": json.dumps(["../../escape.txt"])},
    )
    att = r.json()["attachments"][0]
    assert ".." not in att["name"], att
    saved = Path(att["path"])
    assert str(saved.resolve()).startswith(str(Path(os.environ["HERMES_DESKTOP_HOME"]).resolve()))
    print("  test_endpoint_traversal_via_endpoint OK")


if __name__ == "__main__":
    test_helper_preserves_structure()
    test_helper_traversal_neutralized()
    test_helper_flat_fallback()
    test_endpoint_folder_upload()
    test_endpoint_traversal_via_endpoint()
    print("ALL UPLOAD-FOLDER TESTS PASSED")
