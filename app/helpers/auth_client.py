import json
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple

from app.helpers.resource_path import appdata_dir, resource_path


_LOGIN_FILE = appdata_dir("VisoMaster") / "login.json"
_MOCK_LOGIN_FILE = resource_path("config", "mock_login.json")


@dataclass
class LoginData:
    username: str = ""
    password: str = ""
    remember: bool = False


def load_saved_login() -> LoginData:
    if not _LOGIN_FILE.is_file():
        return LoginData()
    try:
        data = json.loads(_LOGIN_FILE.read_text(encoding="utf-8"))
        return LoginData(
            username=data.get("username", ""),
            password=data.get("password", ""),
            remember=bool(data.get("remember", False)),
        )
    except Exception:
        return LoginData()


def save_login(data: LoginData):
    if not data.remember:
        if _LOGIN_FILE.exists():
            _LOGIN_FILE.unlink(missing_ok=True)
        return
    payload = {"username": data.username, "password": data.password, "remember": data.remember}
    _LOGIN_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def validate_credentials(username: str, password: str) -> Tuple[bool, str]:
    """
    Placeholder validation:
    1) If config/mock_login.json exists and匹配，则通过（便于假登录，后续接入后端删除）。
    2) 否则仅检查非空。
    """
    if not username or not password:
        return False, "账号或密码不能为空"

    if _MOCK_LOGIN_FILE.is_file():
        try:
            data = json.loads(_MOCK_LOGIN_FILE.read_text(encoding="utf-8"))
            if username == data.get("username") and password == data.get("password"):
                return True, ""
            return False, "账号或密码错误（本地配置）"
        except Exception:
            return False, "读取本地账号失败"

    return True, ""
