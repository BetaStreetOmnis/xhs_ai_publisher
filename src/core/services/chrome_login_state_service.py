from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, List, Optional

from playwright.sync_api import sync_playwright

from .chrome_profile_service import ChromeProfilesDetection, detect_chrome_profiles


@dataclass
class ChromeLoginStateImportResult:
    profile_directory: str
    user_data_dir: str
    cookies_file: str
    storage_state_file: str
    imported_cookie_count: int = 0


def is_xhs_cookie(cookie: Dict[str, object]) -> bool:
    try:
        domain = str(cookie.get("domain") or "")
        url = str(cookie.get("url") or "")
        return ("xiaohongshu.com" in domain) or ("xiaohongshu.com" in url)
    except Exception:
        return False


def is_xhs_origin(origin: str) -> bool:
    return "xiaohongshu.com" in str(origin or "")


def ordered_profile_directories(
    detected: Optional[ChromeProfilesDetection],
    preferred_profile_directory: str = "",
) -> List[str]:
    if not detected or not detected.profiles:
        return []

    seen = set()
    ordered: List[str] = []

    def add(directory: str) -> None:
        directory = str(directory or "").strip()
        if not directory or directory in seen:
            return
        seen.add(directory)
        ordered.append(directory)

    add(preferred_profile_directory)
    add(getattr(detected, "default_profile_directory", "") or "")
    for profile in detected.profiles:
        add(getattr(profile, "directory", "") or "")
    return ordered


def filter_xhs_state(raw_state: Optional[Dict[str, object]]) -> Dict[str, object]:
    cookies = []
    try:
        cookies = list((raw_state or {}).get("cookies") or [])
    except Exception:
        cookies = []
    cookies = [cookie for cookie in cookies if isinstance(cookie, dict) and is_xhs_cookie(cookie)]

    origins = []
    try:
        origins = list((raw_state or {}).get("origins") or [])
    except Exception:
        origins = []

    kept_origins = []
    for origin_entry in origins:
        if not isinstance(origin_entry, dict):
            continue
        origin = str(origin_entry.get("origin") or "").strip()
        if origin and is_xhs_origin(origin):
            kept_origins.append(origin_entry)

    return {"cookies": cookies, "origins": kept_origins}


def _backup_file(path: str) -> None:
    try:
        if not path or not os.path.exists(path) or os.path.getsize(path) <= 0:
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = f"{path}.bak_{ts}"
        with open(path, "rb") as rf, open(bak, "wb") as wf:
            wf.write(rf.read())
    except Exception:
        pass


def _copy_profile_to_temp(*, user_data_dir: str, profile_dir: str) -> str:
    src_root = os.path.abspath(os.path.expanduser(str(user_data_dir or "").strip()))
    src_profile = os.path.join(src_root, str(profile_dir or "Default").strip() or "Default")
    if not os.path.isdir(src_root):
        raise RuntimeError(f"Chrome 用户数据目录不存在: {src_root}")
    if not os.path.isdir(src_profile):
        raise RuntimeError(f"Chrome Profile 目录不存在: {src_profile}")

    temp_root = tempfile.mkdtemp(prefix="xhs_chrome_auto_import_")
    try:
        local_state_src = os.path.join(src_root, "Local State")
        if os.path.exists(local_state_src):
            shutil.copy2(local_state_src, os.path.join(temp_root, "Local State"))
    except Exception:
        pass

    dst_profile = os.path.join(temp_root, os.path.basename(src_profile))
    shutil.copytree(src_profile, dst_profile, dirs_exist_ok=True)
    return temp_root


def _is_system_chrome_running() -> bool:
    try:
        import subprocess

        if sys.platform == "darwin":
            result = subprocess.run(["pgrep", "-x", "Google Chrome"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            return result.returncode == 0
        if sys.platform == "win32":
            result = subprocess.run(["tasklist", "/FI", "IMAGENAME eq chrome.exe"], capture_output=True, text=True, check=False)
            return "chrome.exe" in (result.stdout or "").lower()
        result = subprocess.run(["pgrep", "-x", "chrome"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return result.returncode == 0
    except Exception:
        return False


def _check_creator_logged_in(context) -> bool:
    try:
        resp = context.request.get(
            "https://creator.xiaohongshu.com/api/galaxy/user/info",
            timeout=10_000,
        )
        status = int(getattr(resp, "status", 0) or 0)
        try:
            resp.dispose()
        except Exception:
            pass
        return status == 200
    except Exception:
        return False


def import_login_state_from_system_chrome(
    *,
    target_storage_dir: str,
    chrome_user_data_dir: str = "",
    preferred_profile_directory: str = "",
    timeout_s: int = 0,
    allow_manual_wait: bool = False,
    allow_when_chrome_running: bool = False,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Optional[ChromeLoginStateImportResult]:
    target_storage_dir = os.path.abspath(os.path.expanduser(str(target_storage_dir or "").strip()))
    if not target_storage_dir:
        raise ValueError("target_storage_dir 不能为空")
    os.makedirs(target_storage_dir, exist_ok=True)

    cookies_file = os.path.join(target_storage_dir, "xiaohongshu_cookies.json")
    storage_state_file = os.path.join(target_storage_dir, "xiaohongshu_storage_state.json")

    def emit(message: str) -> None:
        if callable(progress_callback):
            try:
                progress_callback(str(message or "").strip())
            except Exception:
                pass

    detected = detect_chrome_profiles(chrome_user_data_dir)
    if not detected:
        return None

    profile_dirs = ordered_profile_directories(detected, preferred_profile_directory)
    if not profile_dirs:
        return None

    if _is_system_chrome_running() and not allow_when_chrome_running:
        emit("检测到系统 Chrome 正在运行，跳过自动导入登录态以避免额外打开多个窗口")
        return None

    last_error = None
    for profile_dir in profile_dirs:
        temp_user_data_dir = ""
        try:
            emit(f"尝试识别系统 Chrome 登录态: {profile_dir}")
            temp_user_data_dir = _copy_profile_to_temp(
                user_data_dir=str(detected.user_data_dir),
                profile_dir=profile_dir,
            )

            with sync_playwright() as p:
                ctx = None
                launch_error = None
                launch_args = ["--start-maximized"]
                if profile_dir and not any(arg.startswith("--profile-directory=") for arg in launch_args):
                    launch_args.append(f"--profile-directory={profile_dir}")

                for attempt in ({"channel": "chrome"}, {}):
                    try:
                        ctx = p.chromium.launch_persistent_context(
                            temp_user_data_dir,
                            headless=False,
                            timeout=120_000,
                            args=launch_args,
                            **attempt,
                        )
                        break
                    except Exception as exc:
                        launch_error = exc
                        ctx = None

                if not ctx:
                    raise RuntimeError(f"启动系统 Chrome 失败: {launch_error}")

                try:
                    pages = list(ctx.pages or [])
                    page = pages[0] if pages else ctx.new_page()
                    for extra_page in pages[1:]:
                        try:
                            extra_page.close()
                        except Exception:
                            pass
                    for url in (
                        "https://creator.xiaohongshu.com/new/home",
                        "https://www.xiaohongshu.com/",
                    ):
                        try:
                            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                            time.sleep(1.2)
                        except Exception:
                            pass

                    logged_in = _check_creator_logged_in(ctx)
                    if not logged_in and allow_manual_wait and timeout_s > 0:
                        emit(f"等待系统 Chrome Profile 完成登录验证: {profile_dir}")
                        deadline = time.time() + float(timeout_s)
                        while time.time() < deadline:
                            if _check_creator_logged_in(ctx):
                                logged_in = True
                                break
                            time.sleep(3)

                    if not logged_in:
                        continue

                    raw_state = ctx.storage_state()
                finally:
                    try:
                        ctx.close()
                    except Exception:
                        pass

            state = filter_xhs_state(raw_state)
            if not state.get("cookies") and not state.get("origins"):
                continue

            _backup_file(cookies_file)
            _backup_file(storage_state_file)
            with open(cookies_file, "w", encoding="utf-8") as f:
                json.dump(state.get("cookies") or [], f, ensure_ascii=False)
            with open(storage_state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False)

            emit(f"已识别到小红书登录态并导入: {profile_dir}")
            return ChromeLoginStateImportResult(
                profile_directory=profile_dir,
                user_data_dir=str(detected.user_data_dir),
                cookies_file=cookies_file,
                storage_state_file=storage_state_file,
                imported_cookie_count=len(state.get("cookies") or []),
            )
        except Exception as exc:
            last_error = exc
        finally:
            if temp_user_data_dir:
                try:
                    shutil.rmtree(temp_user_data_dir, ignore_errors=True)
                except Exception:
                    pass

    if last_error:
        raise RuntimeError(f"自动识别系统 Chrome 登录态失败: {last_error}")
    return None
