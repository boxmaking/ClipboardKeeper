#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ClipboardKeeper —— Windows 后台剪贴板自动记录器

静默驻留后台, 自动捕获系统剪贴板中的文本与图片, 带毫秒级时间戳
写入纯文本日志 (UTF-8), 按月归档, 并附带图片附件目录。

Copyright (C) 2026 pengshao

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

SPDX-License-Identifier: GPL-2.0-or-later
"""

from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import hashlib
import io
import json
import os
import re
import struct
import sys
import threading
import time
import traceback
from datetime import datetime

__version__ = "2.1.0"
__author__ = "pengshao"
__license__ = "GPL-2.0-or-later"
__url__ = "https://github.com/pengshao/ClipboardKeeper"

# ---------------------------------------------------------------- 路径与常量

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_PATH = os.path.join(LOG_DIR, "clipboard_keeper.log")
STATE_PATH = os.path.join(LOG_DIR, "last_hash.txt")
PID_PATH = os.path.join(BASE_DIR, "run.pid")
MUTEX_NAME = "Local\\ClipboardKeeper_SingleInstance"

TEXT_ENCODING = "utf-8"
LINE_WIDTH = 72
SEP = "-" * LINE_WIDTH
HEAD = "=" * LINE_WIDTH

CF_UNICODETEXT = 13
CF_DIB = 8

# 托盘相关
TRAY_CLASS = "ClipboardKeeperTrayWnd"
TRAY_ICON_PATH = os.path.join(LOG_DIR, "tray.ico")
WM_TRAY_CALLBACK = 0x8000 + 1
NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
NIF_MESSAGE, NIF_ICON, NIF_TIP, NIF_INFO = 0x1, 0x2, 0x4, 0x10
MF_STRING, MF_SEPARATOR, MF_GRAYED = 0x0, 0x800, 0x1
TPM_RIGHTBUTTON, TPM_RETURNCMD = 0x2, 0x100
IMAGE_ICON, LR_LOADFROMFILE = 1, 0x10
IDI_APPLICATION = 32512
CMD_OPEN_TODAY, CMD_OPEN_DIR, CMD_OPEN_CONFIG = 1, 2, 3
CMD_OPEN_LOG, CMD_TOGGLE_PAUSE, CMD_QUIT = 4, 5, 9
CMD_STATUS_LINE = 100

DEFAULT_CONFIG = {
    "output_dir": "history",
    "group_by": "month",
    "poll_interval": 0.8,
    "capture_text": True,
    "capture_images": True,
    "image_format": "png",
    "image_quality": 92,
    "image_max_side": 0,
    "max_text_length": 200000,
    "ignore_patterns": [],
    "log_enabled": True,
    "log_max_bytes": 2097152,
    "tray_enabled": True,
    "console_echo": False,
}

CONFIG_TYPES = {
    "output_dir": str,
    "group_by": str,
    "poll_interval": float,
    "capture_text": bool,
    "capture_images": bool,
    "image_format": str,
    "image_quality": int,
    "image_max_side": int,
    "max_text_length": int,
    "ignore_patterns": list,
    "log_enabled": bool,
    "log_max_bytes": int,
    "tray_enabled": bool,
    "console_echo": bool,
}

CONFIG_COMMENTS = {
    "output_dir": "记录根目录，相对路径基于本程序所在目录",
    "group_by": "分文件粒度: month=按月 / day=按天",
    "poll_interval": "轮询间隔(秒)，最小 0.2",
    "capture_text": "是否记录文本",
    "capture_images": "是否记录图片",
    "image_format": "图片格式: png(无损) / jpg(体积小)",
    "image_quality": "jpg 质量，1-100",
    "image_max_side": "图片最长边上限(像素)，0 表示不缩放",
    "max_text_length": "单条文本最大保存字符数，超出截断",
    "ignore_patterns": "正则列表，命中则不记录，例如 [\"^password\"]",
    "log_enabled": "是否写运行日志",
    "log_max_bytes": "日志轮转阈值(字节)",
    "tray_enabled": "是否在任务栏通知区域显示托盘图标",
    "console_echo": "是否把每条记录回显到控制台",
}

# ---------------------------------------------------------------- Win32 绑定

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32", use_last_error=True)

user32.OpenClipboard.argtypes = [wt.HWND]
user32.OpenClipboard.restype = wt.BOOL
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wt.BOOL
user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = wt.BOOL
user32.GetClipboardData.argtypes = [wt.UINT]
user32.GetClipboardData.restype = wt.HANDLE
user32.IsClipboardFormatAvailable.argtypes = [wt.UINT]
user32.IsClipboardFormatAvailable.restype = wt.BOOL
user32.GetClipboardSequenceNumber.argtypes = []
user32.GetClipboardSequenceNumber.restype = wt.DWORD
kernel32.GlobalLock.argtypes = [wt.HGLOBAL]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [wt.HGLOBAL]
kernel32.GlobalUnlock.restype = wt.BOOL
kernel32.GlobalSize.argtypes = [wt.HGLOBAL]
kernel32.GlobalSize.restype = ctypes.c_size_t

# ---- 托盘所需绑定
LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM)


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wt.DWORD),
        ("hWnd", wt.HWND),
        ("uID", wt.UINT),
        ("uFlags", wt.UINT),
        ("uCallbackMessage", wt.UINT),
        ("hIcon", wt.HICON),
        ("szTip", wt.WCHAR * 128),
        ("dwState", wt.DWORD),
        ("dwStateMask", wt.DWORD),
        ("szInfo", wt.WCHAR * 256),
        ("uVersion", wt.UINT),
        ("szInfoTitle", wt.WCHAR * 64),
        ("dwInfoFlags", wt.DWORD),
        ("guidItem", ctypes.c_byte * 16),
        ("hBalloonIcon", wt.HICON),
    ]


class WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wt.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wt.HINSTANCE),
        ("hIcon", wt.HICON),
        ("hCursor", wt.HANDLE),
        ("hbrBackground", wt.HBRUSH),
        ("lpszMenuName", wt.LPCWSTR),
        ("lpszClassName", wt.LPCWSTR),
    ]


user32.DefWindowProcW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.DefWindowProcW.restype = LRESULT
user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
user32.RegisterClassW.restype = wt.ATOM
user32.CreateWindowExW.argtypes = [wt.DWORD, wt.LPCWSTR, wt.LPCWSTR, wt.DWORD,
                                   ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                   wt.HWND, wt.HMENU, wt.HINSTANCE, wt.LPVOID]
user32.CreateWindowExW.restype = wt.HWND
user32.DestroyWindow.argtypes = [wt.HWND]
user32.DestroyWindow.restype = wt.BOOL
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.PostMessageW.restype = wt.BOOL
user32.GetMessageW.argtypes = [ctypes.POINTER(wt.MSG), wt.HWND, wt.UINT, wt.UINT]
user32.GetMessageW.restype = ctypes.c_int
user32.TranslateMessage.argtypes = [ctypes.POINTER(wt.MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wt.MSG)]
user32.DispatchMessageW.restype = LRESULT
user32.LoadIconW.argtypes = [wt.HINSTANCE, ctypes.c_void_p]
user32.LoadIconW.restype = wt.HICON
user32.LoadImageW.argtypes = [wt.HINSTANCE, wt.LPCWSTR, wt.UINT,
                              ctypes.c_int, ctypes.c_int, wt.UINT]
user32.LoadImageW.restype = wt.HANDLE
user32.CreatePopupMenu.restype = wt.HMENU
user32.AppendMenuW.argtypes = [wt.HMENU, wt.UINT, ctypes.c_size_t, wt.LPCWSTR]
user32.AppendMenuW.restype = wt.BOOL
user32.DestroyMenu.argtypes = [wt.HMENU]
user32.DestroyMenu.restype = wt.BOOL
user32.TrackPopupMenu.argtypes = [wt.HMENU, wt.UINT, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_int, wt.HWND, ctypes.c_void_p]
user32.TrackPopupMenu.restype = ctypes.c_int
user32.SetForegroundWindow.argtypes = [wt.HWND]
user32.SetForegroundWindow.restype = wt.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
user32.GetCursorPos.restype = wt.BOOL
shell32.Shell_NotifyIconW.argtypes = [wt.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
shell32.Shell_NotifyIconW.restype = wt.BOOL
kernel32.GetModuleHandleW.argtypes = [wt.LPCWSTR]
kernel32.GetModuleHandleW.restype = wt.HMODULE


# ---------------------------------------------------------------- 基础工具

def echo(msg=""):
    """向控制台输出，无控制台时静默忽略"""
    try:
        if sys.stdout:
            sys.stdout.write(str(msg) + "\n")
            sys.stdout.flush()
    except Exception:
        pass


def log(msg, enabled=True, level="INFO"):
    """写运行日志，超阈值自动轮转"""
    if not enabled:
        return
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        limit = int(DEFAULT_CONFIG["log_max_bytes"])
        if os.path.exists(LOG_PATH) and os.path.getsize(LOG_PATH) > limit:
            try:
                os.replace(LOG_PATH, LOG_PATH + ".1")
            except Exception:
                pass
        line = "[%s] [%s] %s\n" % (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"), level, msg)
        with open(LOG_PATH, "a", encoding=TEXT_ENCODING) as f:
            f.write(line)
    except Exception:
        pass


def resolve_path(path):
    """相对路径按程序所在目录展开"""
    if not path:
        return BASE_DIR
    path = os.path.expandvars(os.path.expanduser(str(path)))
    if not os.path.isabs(path):
        path = os.path.join(BASE_DIR, path)
    return os.path.normpath(path)


def human_size(num):
    num = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024 or unit == "GB":
            return "%.1f %s" % (num, unit) if unit != "B" else "%d B" % num
        num /= 1024.0
    return "%.1f GB" % num


# ---------------------------------------------------------------- 配置

def write_default_config(cfg):
    """首次运行时生成带注释的 config.json"""
    lines = ["{"]
    items = list(cfg.items())
    for i, (k, v) in enumerate(items):
        tail = "," if i < len(items) - 1 else ""
        comment = CONFIG_COMMENTS.get(k)
        prefix = "  // %s\n" % comment if comment else ""
        lines.append("%s  %s: %s%s" % (prefix, json.dumps(k, ensure_ascii=False),
                                       json.dumps(v, ensure_ascii=False), tail))
    lines.append("}")
    body = "// ClipboardKeeper 配置文件 (允许 // 注释)\n" + "\n".join(lines) + "\n"
    with open(CONFIG_PATH, "w", encoding=TEXT_ENCODING) as f:
        f.write(body)


def strip_json_comments(text):
    """移除 // 与 /* */ 注释(不触碰字符串内部)"""
    out = []
    i, n = 0, len(text)
    in_str = False
    escape = False
    while i < n:
        ch = text[i]
        if in_str:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] not in "\r\n":
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def coerce_config(user):
    """按类型约束修正用户配置，非法项回退默认值"""
    cfg = dict(DEFAULT_CONFIG)
    for key, value in (user or {}).items():
        if key not in DEFAULT_CONFIG:
            continue
        want = CONFIG_TYPES.get(key)
        try:
            if want is bool:
                cfg[key] = bool(value)
            elif want is int:
                cfg[key] = int(value)
            elif want is float:
                cfg[key] = float(value)
            elif want is list:
                cfg[key] = list(value) if isinstance(value, (list, tuple)) else cfg[key]
            else:
                cfg[key] = str(value)
        except (TypeError, ValueError):
            pass
    cfg["poll_interval"] = max(0.2, min(60.0, float(cfg["poll_interval"])))
    cfg["image_quality"] = max(1, min(100, int(cfg["image_quality"])))
    cfg["image_max_side"] = max(0, int(cfg["image_max_side"]))
    cfg["image_format"] = str(cfg["image_format"]).lower().strip(".")
    if cfg["image_format"] not in ("png", "jpg", "jpeg"):
        cfg["image_format"] = "png"
    if str(cfg["group_by"]).lower() not in ("month", "day"):
        cfg["group_by"] = "month"
    cfg["group_by"] = str(cfg["group_by"]).lower()
    return cfg


def load_config():
    if not os.path.exists(CONFIG_PATH):
        write_default_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
            raw = f.read()
        return coerce_config(json.loads(strip_json_comments(raw)))
    except Exception:
        log("config.json 解析失败, 回退默认配置: %s" % traceback.format_exc())
        return dict(DEFAULT_CONFIG)


# ---------------------------------------------------------------- 剪贴板读取

def clipboard_sequence():
    """系统剪贴板序号，内容变化才会递增"""
    try:
        return int(user32.GetClipboardSequenceNumber())
    except Exception:
        return 0


def read_clipboard_text():
    if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
        return None
    if not user32.OpenClipboard(None):
        return None
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return None
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return None
        try:
            return ctypes.wstring_at(ptr)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def read_clipboard_dib():
    """返回剪贴板中的 DIB 原始字节，无则 None"""
    if not user32.IsClipboardFormatAvailable(CF_DIB):
        return None
    if not user32.OpenClipboard(None):
        return None
    try:
        handle = user32.GetClipboardData(CF_DIB)
        if not handle:
            return None
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return None
        try:
            size = kernel32.GlobalSize(handle)
            if not size or size < 40:
                return None
            return ctypes.string_at(ptr, size)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def dib_to_image(dib):
    """把 DIB 字节补上 BMP 文件头后交给 Pillow，缺少 Pillow 时返回 None"""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        bi_size = struct.unpack("<I", dib[0:4])[0]
        bit_count = struct.unpack("<H", dib[14:16])[0]
        clr_used = struct.unpack("<I", dib[32:36])[0]
        palette = 0
        if bit_count <= 8:
            palette = (clr_used or (1 << bit_count)) * 4
        off_bits = 14 + bi_size + palette
        header = struct.pack("<2sIHHI", b"BM", 14 + len(dib), 0, 0, off_bits)
        return Image.open(io.BytesIO(header + dib))
    except Exception:
        log("DIB 解析失败: %s" % traceback.format_exc())
        return None


# ---------------------------------------------------------------- 落盘

def ensure_dirs(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    img_dir = os.path.join(output_dir, "images")
    os.makedirs(img_dir, exist_ok=True)
    return {"root": output_dir, "images": img_dir}


def append_record(path, period, ts, tag, body):
    """向月度文本追加一条记录"""
    new_file = not os.path.exists(path)
    with open(path, "a", encoding=TEXT_ENCODING) as f:
        if new_file:
            f.write("剪贴板记录  %s\n" % period)
            f.write(HEAD + "\n\n")
        f.write("[%s] %s\n" % (ts, tag))
        f.write(SEP + "\n")
        f.write(body.rstrip("\r\n") + "\n\n")


def load_last_hash():
    try:
        if os.path.exists(STATE_PATH):
            with open(STATE_PATH, "r", encoding=TEXT_ENCODING) as f:
                return f.read().strip() or None
    except Exception:
        pass
    return None


def save_last_hash(digest):
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(STATE_PATH, "w", encoding=TEXT_ENCODING) as f:
            f.write(digest or "")
    except Exception:
        pass


def read_pid():
    try:
        with open(PID_PATH, "r", encoding=TEXT_ENCODING) as f:
            return int(f.read().strip())
    except Exception:
        return None


def pid_alive(pid):
    if not pid:
        return False
    try:
        kernel32.OpenProcess.restype = wt.HANDLE
        kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
        handle = kernel32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if handle:
            kernel32.CloseHandle(handle)
            return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------- 核心

class Keeper(object):
    """剪贴板监听与落盘"""

    def __init__(self, cfg, echo_enabled=False):
        self.cfg = cfg
        self.console = echo_enabled or bool(cfg.get("console_echo"))
        self.output_dir = resolve_path(cfg.get("output_dir"))
        self.dirs = ensure_dirs(self.output_dir)
        self.ignore_res = self._compile_ignore(cfg.get("ignore_patterns"))
        self.last_hash = load_last_hash()
        self.last_seq = None
        self.cfg_mtime = self._config_mtime()
        self.running = True
        self.paused = False
        self.on_record = None
        self.stats = {"text": 0, "image": 0, "skip": 0, "start": datetime.now()}

    # -------------------------------------------------- 记录统计回调

    def _notify_change(self):
        cb = self.on_record
        if cb:
            try:
                cb()
            except Exception:
                pass

    def pause(self):
        self.paused = True
        log("监听已暂停")
        self._notify_change()

    def resume(self):
        self.paused = False
        log("监听已恢复")
        self._notify_change()

    def toggle_pause(self):
        if self.paused:
            self.resume()
        else:
            self.pause()
        return self.paused

    # -------------------------------------------------- 配置

    @staticmethod
    def _config_mtime():
        try:
            return os.path.getmtime(CONFIG_PATH)
        except Exception:
            return 0

    @staticmethod
    def _compile_ignore(patterns):
        compiled = []
        for pat in patterns or []:
            try:
                compiled.append(re.compile(str(pat)))
            except re.error:
                log("忽略规则无效, 已跳过: %r" % pat, level="WARN")
        return compiled

    def reload_config(self):
        """config.json 变动后热加载，无需重启"""
        cfg = load_config()
        self.cfg = cfg
        new_out = resolve_path(cfg.get("output_dir"))
        if new_out != self.output_dir:
            self.output_dir = new_out
            self.dirs = ensure_dirs(new_out)
            log("输出目录已切换: %s" % new_out)
        self.ignore_res = self._compile_ignore(cfg.get("ignore_patterns"))
        self.console = bool(cfg.get("console_echo")) or self.console
        self.cfg_mtime = self._config_mtime()
        log("配置已热加载")

    def maybe_reload(self):
        mtime = self._config_mtime()
        if mtime and mtime != self.cfg_mtime:
            try:
                self.reload_config()
            except Exception:
                log("配置热加载失败: %s" % traceback.format_exc(), level="ERROR")

    # -------------------------------------------------- 判定

    def _ignored(self, text):
        for pattern in self.ignore_res:
            try:
                if pattern.search(text):
                    return True
            except Exception:
                pass
        return False

    def period_path(self):
        now = datetime.now()
        period = now.strftime("%Y-%m-%d" if self.cfg["group_by"] == "day" else "%Y-%m")
        return now, period, os.path.join(self.dirs["root"], period + ".txt")

    # -------------------------------------------------- 记录

    def save_text(self, text):
        limit = int(self.cfg.get("max_text_length", 200000))
        if len(text) > limit:
            stored = text[:limit] + "\n…（已截断，原文 %d 字符）" % len(text)
        else:
            stored = text
        now, period, path = self.period_path()
        ts = now.strftime("%Y-%m-%d %H:%M:%S.") + "%03d" % (now.microsecond // 1000)
        append_record(path, period, ts, "文本 · %d 字符" % len(text), stored)
        self.stats["text"] += 1
        if self.console:
            head = text.strip().splitlines()[0][:60] if text.strip() else "(空行)"
            echo("[%s] 文本 %d 字符  %s" % (ts, len(text), head))
        log("记录文本 %d 字符" % len(text), self.cfg.get("log_enabled", True))
        self._notify_change()
        return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()

    def save_image(self, dib):
        image = dib_to_image(dib)
        if image is None:
            return None
        fmt = self.cfg.get("image_format", "png")
        ext = "jpg" if fmt in ("jpg", "jpeg") else "png"
        try:
            max_side = int(self.cfg.get("image_max_side", 0))
            if max_side > 0 and max(image.size) > max_side:
                image.thumbnail((max_side, max_side))
            now, period, path = self.period_path()
            name = now.strftime("%Y-%m-%d_%H%M%S_") + "%03d" % (now.microsecond // 1000)
            fname = "%s.%s" % (name, ext)
            fpath = os.path.join(self.dirs["images"], fname)
            if ext == "jpg":
                image.convert("RGB").save(fpath, "JPEG", quality=int(self.cfg.get("image_quality", 92)),
                                          optimize=True)
            else:
                image.save(fpath, "PNG")
        except Exception:
            log("图片保存失败: %s" % traceback.format_exc(), self.cfg.get("log_enabled", True), "ERROR")
            return None
        ts = now.strftime("%Y-%m-%d %H:%M:%S.") + "%03d" % (now.microsecond // 1000)
        append_record(path, period, ts, "图片 · %d×%d" % (image.width, image.height),
                      "图片文件: images\\" + fname)
        self.stats["image"] += 1
        if self.console:
            echo("[%s] 图片 %dx%d -> %s" % (ts, image.width, image.height, fname))
        log("记录图片 %dx%d -> %s" % (image.width, image.height, fname),
            self.cfg.get("log_enabled", True))
        self._notify_change()
        return hashlib.sha1(dib).hexdigest()

    # -------------------------------------------------- 轮询

    def poll_once(self):
        seq = clipboard_sequence()
        if seq and seq == self.last_seq:
            return False
        if seq:
            self.last_seq = seq

        touched = False
        # 图片优先: 截图类内容常同时带文本/文件引用，以位图为准
        if self.cfg.get("capture_images", True):
            dib = read_clipboard_dib()
            if dib:
                digest = hashlib.sha1(dib).hexdigest()
                if digest != self.last_hash:
                    saved = self.save_image(dib)
                    if saved:
                        self.last_hash = saved
                        save_last_hash(saved)
                        touched = True
                else:
                    self.stats["skip"] += 1
                return touched
            if dib is None and not self.cfg.get("capture_text", True):
                self.last_seq = None
                return False

        if self.cfg.get("capture_text", True):
            text = read_clipboard_text()
            if text is None:
                # 读取失败(剪贴板被占用)时不记账，下轮重试
                self.last_seq = None
                return False
            if text.strip() and not self._ignored(text):
                digest = hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()
                if digest != self.last_hash:
                    self.last_hash = self.save_text(text)
                    save_last_hash(self.last_hash)
                    touched = True
                else:
                    self.stats["skip"] += 1
            elif not text.strip():
                self.stats["skip"] += 1
        return touched

    def run(self, max_cycles=0):
        log("ClipboardKeeper %s 启动 | 输出 %s | 粒度 %s | 轮询 %.2fs | 图片 %s"
            % (__version__, self.output_dir, self.cfg["group_by"],
               self.cfg["poll_interval"], self.cfg.get("image_format", "png")),
            self.cfg.get("log_enabled", True))
        interval = max(0.2, float(self.cfg.get("poll_interval", 0.8)))
        cycles = 0
        last_reload_check = 0.0
        while self.running:
            try:
                stamp = time.time()
                if stamp - last_reload_check >= 2.0:
                    self.maybe_reload()
                    last_reload_check = stamp
                if not self.paused:
                    self.poll_once()
                else:
                    # 暂停期间丢弃已发生的变化，恢复后从当前剪贴板重新开始
                    self.last_seq = None
            except Exception:
                log("轮询异常: %s" % traceback.format_exc(), self.cfg.get("log_enabled", True), "ERROR")
            cycles += 1
            if max_cycles and cycles >= max_cycles:
                break
            time.sleep(interval)

    def stop(self, *_args):
        self.running = False


# ---------------------------------------------------------------- 托盘图标

def make_tray_icon():
    """生成托盘图标文件(首次运行)，返回 HICON；全过程失败则回退系统图标"""
    try:
        if not os.path.exists(TRAY_ICON_PATH):
            from PIL import Image, ImageDraw
            size = 256
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.rounded_rectangle([6, 6, 250, 250], radius=58, fill=(30, 90, 150, 255))
            d.rounded_rectangle([62, 44, 194, 232], radius=18, fill=(255, 255, 255, 255))
            d.rounded_rectangle([104, 24, 152, 70], radius=12, fill=(224, 232, 244, 255))
            d.rounded_rectangle([116, 38, 140, 56], radius=7, fill=(30, 90, 150, 255))
            for y in (100, 138, 176):
                d.rounded_rectangle([88, y, 168, y + 14], radius=7, fill=(30, 90, 150, 255))
            os.makedirs(LOG_DIR, exist_ok=True)
            img.save(TRAY_ICON_PATH, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (256, 256)])
    except Exception:
        log("生成托盘图标失败, 回退系统图标: %s" % traceback.format_exc(), level="WARN")
    try:
        if os.path.exists(TRAY_ICON_PATH):
            handle = user32.LoadImageW(None, TRAY_ICON_PATH, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
            if handle:
                return handle
    except Exception:
        pass
    try:
        return user32.LoadIconW(None, ctypes.c_void_p(IDI_APPLICATION))
    except Exception:
        return None


class TrayIcon(object):
    """任务栏通知区域图标：独立线程跑消息循环，菜单直接操作 Keeper"""

    def __init__(self, keeper):
        self.keeper = keeper
        self.hwnd = None
        self.hicon = None
        self.nid = None
        self.visible = False
        self._proc_ref = None
        self._thread = None
        self._tip_lock = threading.Lock()
        self._last_tip = 0.0

    # -------------------------------------------------- 生命周期

    def start(self):
        """在后台线程挂载托盘，失败不影响主监听"""
        self._thread = threading.Thread(target=self._run, name="tray", daemon=True)
        self._thread.start()

    def _run(self):
        try:
            self._create_window()
        except Exception:
            log("托盘窗口创建失败, 继续无图标运行: %s" % traceback.format_exc(), level="ERROR")
            return
        try:
            self._add_icon()
        except Exception:
            log("托盘图标挂载失败, 继续无图标运行: %s" % traceback.format_exc(), level="ERROR")
        msg = wt.MSG()
        while True:
            try:
                ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            except Exception:
                break
            if ret == 0 or ret == -1:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
        log("托盘线程退出")

    def _create_window(self):
        hinst = kernel32.GetModuleHandleW(None)
        self.hicon = make_tray_icon()
        self._proc_ref = WNDPROC(self._on_message)
        wc = WNDCLASSW()
        wc.style = 0
        wc.lpfnWndProc = self._proc_ref
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hInstance = hinst
        wc.hIcon = self.hicon
        wc.hCursor = None
        wc.hbrBackground = None
        wc.lpszMenuName = None
        wc.lpszClassName = TRAY_CLASS
        atom = user32.RegisterClassW(ctypes.byref(wc))
        if not atom and ctypes.get_last_error() != 1410:  # ERROR_CLASS_ALREADY_EXISTS
            log("RegisterClassW 失败: %s" % ctypes.get_last_error(), level="WARN")
        self.hwnd = user32.CreateWindowExW(0, TRAY_CLASS, "ClipboardKeeper", 0,
                                           0, 0, 0, 0, None, None, hinst, None)
        if not self.hwnd:
            raise ctypes.WinError(ctypes.get_last_error())

    def _add_icon(self):
        self.nid = NOTIFYICONDATAW()
        self.nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        self.nid.hWnd = self.hwnd
        self.nid.uID = 1
        self.nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        self.nid.uCallbackMessage = WM_TRAY_CALLBACK
        self.nid.hIcon = self.hicon
        self.nid.szTip = self._tip_text()
        if not shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self.nid)):
            raise ctypes.WinError(ctypes.get_last_error())
        self.visible = True
        log("托盘图标已显示")

    def close(self):
        """从任意线程请求退出托盘"""
        try:
            if self.hwnd:
                user32.PostMessageW(self.hwnd, 0x0010, 0, 0)  # WM_CLOSE
            else:
                self._remove_icon()
        except Exception:
            pass

    def _remove_icon(self):
        if self.nid is not None:
            try:
                shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.nid))
            except Exception:
                pass
            self.visible = False

    # -------------------------------------------------- 提示与气泡

    def _tip_text(self):
        k = self.keeper
        state = "已暂停" if k.paused else "运行中"
        tip = "ClipboardKeeper · %s · 文本 %d / 图片 %d" % (
            state, k.stats["text"], k.stats["image"])
        return tip[:127]

    def refresh_tip(self):
        """记录变化后刷新悬浮提示，2 秒内最多刷新一次"""
        if not self.visible or self.nid is None:
            return
        now = time.time()
        if now - self._last_tip < 2.0:
            return
        self._last_tip = now
        try:
            self.nid.szTip = self._tip_text()
            self.nid.uFlags = NIF_TIP
            shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self.nid))
        except Exception:
            pass

    def balloon(self, title, text):
        if not self.visible or self.nid is None:
            return
        try:
            self.nid.uFlags = NIF_INFO
            self.nid.szInfo = str(text)[:255]
            self.nid.szInfoTitle = str(title)[:63]
            self.nid.dwInfoFlags = 0x1  # NIIF_INFO
            shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self.nid))
            self.nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        except Exception:
            pass

    # -------------------------------------------------- 菜单

    def _on_message(self, hwnd, msg, wparam, lparam):
        try:
            if msg == WM_TRAY_CALLBACK:
                event = int(lparam) & 0xFFFF
                if event == 0x0203:          # WM_LBUTTONDBLCLK
                    self._open_today()
                elif event == 0x0205:        # WM_RBUTTONUP
                    self._show_menu()
                return 0
            if msg == 0x0111:                # WM_COMMAND
                self._handle_command(int(wparam) & 0xFFFF)
                return 0
            if msg == 0x0010:                # WM_CLOSE
                self._remove_icon()
                user32.DestroyWindow(hwnd)
                return 0
            if msg == 0x0002:                # WM_DESTROY
                user32.PostQuitMessage(0)
                return 0
        except Exception:
            log("托盘消息处理异常: %s" % traceback.format_exc(), level="ERROR")
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _menu_add(self, hmenu, cmd, text, flags=MF_STRING):
        try:
            user32.AppendMenuW(hmenu, flags, cmd, text)
        except Exception:
            pass

    def _show_menu(self):
        hmenu = user32.CreatePopupMenu()
        if not hmenu:
            return
        cmd = 0
        try:
            k = self.keeper
            self._menu_add(hmenu, CMD_STATUS_LINE, "本次已记录 文本 %d / 图片 %d" % (
                k.stats["text"], k.stats["image"]), MF_STRING | MF_GRAYED)
            self._menu_add(hmenu, 0, "", MF_SEPARATOR)
            self._menu_add(hmenu, CMD_OPEN_TODAY, "打开当月记录文件")
            self._menu_add(hmenu, CMD_OPEN_DIR, "打开归档目录")
            self._menu_add(hmenu, CMD_OPEN_CONFIG, "打开配置文件")
            self._menu_add(hmenu, CMD_OPEN_LOG, "查看运行日志")
            self._menu_add(hmenu, 0, "", MF_SEPARATOR)
            self._menu_add(hmenu, CMD_TOGGLE_PAUSE,
                           "继续监听" if k.paused else "暂停监听")
            self._menu_add(hmenu, 0, "", MF_SEPARATOR)
            self._menu_add(hmenu, CMD_QUIT, "退出 ClipboardKeeper")
            pt = wt.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            user32.SetForegroundWindow(self.hwnd)
            cmd = user32.TrackPopupMenu(hmenu, TPM_RIGHTBUTTON | TPM_RETURNCMD,
                                        pt.x, pt.y, 0, self.hwnd, None)
            user32.PostMessageW(self.hwnd, 0, 0, 0)  # WM_NULL, 让菜单正常收起
        except Exception:
            log("弹出托盘菜单失败: %s" % traceback.format_exc(), level="ERROR")
        finally:
            user32.DestroyMenu(hmenu)
        if cmd:
            self._handle_command(cmd)

    def _handle_command(self, cmd):
        if cmd == CMD_OPEN_TODAY:
            self._open_today()
        elif cmd == CMD_OPEN_DIR:
            self._open_path(self.keeper.output_dir, "归档目录")
        elif cmd == CMD_OPEN_CONFIG:
            self._open_path(CONFIG_PATH, "配置文件")
        elif cmd == CMD_OPEN_LOG:
            self._open_path(LOG_PATH, "运行日志")
        elif cmd == CMD_TOGGLE_PAUSE:
            self.keeper.toggle_pause()
            self.refresh_tip()
            log("托盘操作: %s" % ("恢复监听" if not self.keeper.paused else "暂停监听"))
        elif cmd == CMD_QUIT:
            log("托盘操作: 退出程序")
            self.keeper.running = False
            self.keeper.paused = False

    # -------------------------------------------------- 打开文件

    def _open_today(self):
        now, period, path = self.keeper.period_path()
        if os.path.exists(path):
            self._open_path(path, "当月记录文件")
        else:
            self.balloon("ClipboardKeeper",
                         "本月记录文件尚未生成：%s" % period)

    def _open_path(self, path, label):
        try:
            if not path:
                return
            if os.path.exists(path):
                os.startfile(path)
            else:
                self.balloon("ClipboardKeeper", "%s 不存在：%s" % (label, path))
        except Exception:
            log("打开 %s 失败: %s" % (label, traceback.format_exc()), level="ERROR")
            self.balloon("ClipboardKeeper", "打开%s失败，详见日志" % label)


def create_tray(keeper):
    """挂载托盘图标，并把记录变化接到提示刷新"""
    tray = TrayIcon(keeper)
    tray.start()
    keeper.on_record = tray.refresh_tip
    return tray


# ---------------------------------------------------------------- 进程控制

def acquire_mutex():
    kernel32.CreateMutexW.restype = wt.HANDLE
    handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not handle:
        return None
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        return None
    return handle


def print_status(cfg):
    out_dir = resolve_path(cfg.get("output_dir"))
    pid = read_pid()
    alive = pid_alive(pid)
    echo("ClipboardKeeper %s  (%s)" % (__version__, __license__))
    echo("运行状态 : %s" % (("运行中, PID %d" % pid) if alive else "未运行"))
    echo("输出目录 : %s" % out_dir)
    period = datetime.now().strftime("%Y-%m-%d" if cfg["group_by"] == "day" else "%Y-%m")
    current = os.path.join(out_dir, period + ".txt")
    if os.path.exists(current):
        with open(current, "r", encoding=TEXT_ENCODING, errors="ignore") as f:
            count = sum(1 for line in f if line.startswith("[") and "]" in line[:40])
        echo("当前文件 : %s  (%s, 约 %d 条)"
             % (current, human_size(os.path.getsize(current)), count))
    else:
        echo("当前文件 : %s  (尚未生成)" % current)
    img_dir = os.path.join(out_dir, "images")
    if os.path.isdir(img_dir):
        files = os.listdir(img_dir)
        total = sum(os.path.getsize(os.path.join(img_dir, n)) for n in files
                    if os.path.isfile(os.path.join(img_dir, n)))
        echo("图片目录 : %s  (%d 个文件, %s)" % (img_dir, len(files), human_size(total)))
    echo("配置文件 : %s" % CONFIG_PATH)
    echo("日志文件 : %s" % LOG_PATH)
    echo("")
    echo("关键配置 : 粒度=%s  轮询=%.2fs  文本=%s  图片=%s(%s)  最大字符=%d"
         % (cfg["group_by"], cfg["poll_interval"], cfg["capture_text"],
            cfg["capture_images"], cfg.get("image_format", "png"), cfg["max_text_length"]))


def build_parser():
    parser = argparse.ArgumentParser(
        prog="clipboard_keeper",
        description="ClipboardKeeper —— Windows 后台剪贴板自动记录器",
        epilog="示例: python clipboard_keeper.py --console")
    parser.add_argument("-c", "--console", action="store_true", help="把每条记录回显到控制台")
    parser.add_argument("--once", action="store_true", help="只抓取一次当前剪贴板后退出")
    parser.add_argument("--no-tray", action="store_true", help="本次不显示托盘图标")
    parser.add_argument("--status", action="store_true", help="显示运行状态与统计后退出")
    parser.add_argument("--init-config", action="store_true", help="生成带注释的默认配置文件后退出")
    parser.add_argument("-v", "--version", action="version",
                        version="ClipboardKeeper %s (%s)" % (__version__, __license__))
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    cfg = load_config()

    if args.init_config:
        write_default_config(cfg)
        echo("已生成配置文件: %s" % CONFIG_PATH)
        return 0

    if args.status:
        print_status(cfg)
        return 0

    os.makedirs(LOG_DIR, exist_ok=True)

    if args.once:
        keeper = Keeper(cfg, echo_enabled=True)
        touched = keeper.poll_once()
        echo("抓取完成: %s" % ("已记录一条" if touched else "剪贴板无新内容"))
        return 0

    mutex = acquire_mutex()
    if not mutex:
        echo("已有实例正在运行, 本次启动已退出。")
        return 1

    try:
        with open(PID_PATH, "w", encoding=TEXT_ENCODING) as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

    keeper = Keeper(cfg, echo_enabled=args.console)
    try:
        import signal
        for sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None),
                    getattr(signal, "SIGBREAK", None)):
            if sig is not None:
                try:
                    signal.signal(sig, keeper.stop)
                except Exception:
                    pass
    except Exception:
        pass

    echo("ClipboardKeeper %s 已启动" % __version__)
    echo("输出目录: %s" % keeper.output_dir)
    echo("配置文件: %s" % CONFIG_PATH)
    echo("按 Ctrl+C 停止")

    tray = None
    if cfg.get("tray_enabled", True) and not args.no_tray:
        try:
            tray = create_tray(keeper)
            echo("托盘图标: 已挂载 (任务栏通知区域)")
        except Exception:
            log("托盘启动失败: %s" % traceback.format_exc(), level="ERROR")
            echo("托盘图标: 启动失败, 已降级为静默运行")
    else:
        echo("托盘图标: 已关闭")

    try:
        keeper.run()
    except KeyboardInterrupt:
        echo("\n已停止")
    finally:
        if tray is not None:
            try:
                tray.close()
            except Exception:
                pass
        log("ClipboardKeeper 退出 | 本次记录 文本 %d / 图片 %d / 跳过 %d"
            % (keeper.stats["text"], keeper.stats["image"], keeper.stats["skip"]),
            cfg.get("log_enabled", True))
        try:
            if os.path.exists(PID_PATH):
                os.remove(PID_PATH)
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
