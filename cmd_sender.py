#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cmd_sender - 多Tab文本编辑器，支持向目标窗口发送命令
依赖：仅 Python 标准库 (tkinter, ctypes)
运行环境：Windows (Python 3.10+)
"""

import os
import sys
import time
import ctypes
from ctypes import wintypes

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

# ============================================================================
# Win32 API 常量与结构体定义
# ============================================================================

# SendInput 类型
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

# 键盘事件标志
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

# 虚拟键码
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_MENU = 0x12  # Alt
VK_RETURN = 0x0D
VK_A = 0x41
VK_BACK = 0x08
VK_DELETE = 0x2E

# 窗口消息
WM_SETTEXT = 0x000C
WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E

# 窗口显示状态
SW_RESTORE = 9
SW_SHOW = 5

# 鼠标事件
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", _INPUT_UNION),
    ]


# 加载 user32 和 kernel32
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 设置函数原型
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL

user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = wintypes.BOOL

user32.WindowFromPoint.argtypes = [POINT]
user32.WindowFromPoint.restype = wintypes.HWND

user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND

user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int

user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int

user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int

user32.SetCapture.argtypes = [wintypes.HWND]
user32.SetCapture.restype = wintypes.HWND

user32.ReleaseCapture.argtypes = []
user32.ReleaseCapture.restype = wintypes.BOOL

user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wintypes.BOOL

user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL

user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL

user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL

user32.SendInput.argtypes = [
    wintypes.UINT,
    ctypes.POINTER(INPUT),
    ctypes.c_int,
]
user32.SendInput.restype = wintypes.UINT

user32.GetMessageExtraInfo.argtypes = []
user32.GetMessageExtraInfo.restype = ctypes.POINTER(ctypes.c_ulong)

user32.GetKeyState.argtypes = [ctypes.c_int]
user32.GetKeyState.restype = wintypes.SHORT

user32.SystemParametersInfoW.argtypes = [
    wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT
]
user32.SystemParametersInfoW.restype = wintypes.BOOL

user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD

GA_ROOT = 2


def get_window_text(hwnd):
    """获取窗口标题"""
    length = user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def get_window_class(hwnd):
    """获取窗口类名"""
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def get_cursor_pos():
    """获取当前鼠标位置"""
    pt = POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def window_from_point(x, y):
    """获取鼠标下方的顶层窗口句柄（自动解析到根窗口）"""
    pt = POINT(x, y)
    child_hwnd = user32.WindowFromPoint(pt)
    if child_hwnd:
        return user32.GetAncestor(child_hwnd, GA_ROOT)
    return None


def get_window_rect(hwnd):
    """获取窗口矩形区域"""
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return rect.left, rect.top, rect.right, rect.bottom


def get_current_process_id():
    """获取当前进程的 PID"""
    return kernel32.GetCurrentProcessId()


def is_own_window(hwnd):
    """检查窗口是否属于当前进程"""
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value == get_current_process_id()


# ============================================================================
# TargetWindow - 管理目标窗口信息
# ============================================================================

class TargetWindow:
    """管理绑定的目标窗口 HWND"""

    def __init__(self):
        self.hwnd = None
        self.title = ""
        self.class_name = ""

    def bind(self, hwnd):
        """绑定到指定窗口"""
        self.hwnd = hwnd
        self.title = get_window_text(hwnd)
        self.class_name = get_window_class(hwnd)

    def clear(self):
        """清除绑定"""
        self.hwnd = None
        self.title = ""
        self.class_name = ""

    def is_valid(self):
        """检查绑定是否有效"""
        if not self.hwnd:
            return False
        return bool(user32.IsWindow(self.hwnd))

    def get_display_text(self):
        """获取用于界面显示的文本"""
        if not self.hwnd:
            return "未绑定窗口"
        if not self.is_valid():
            return "窗口已关闭"
        return f"{self.title} ({self.class_name})"


# ============================================================================
# Sender - 使用 Win32 SendInput 发送文本
# ============================================================================

class Sender:
    """通过 SendInput 模拟键盘输入发送文本到目标窗口"""

    @staticmethod
    def send_text(hwnd, text, press_enter=False, clear_first=False):
        """
        向目标窗口发送文本

        参数:
            hwnd: 目标窗口句柄
            text: 要发送的文本
            press_enter: 是否在文本后附加 Enter
            clear_first: 是否先发送 Ctrl+A 全选清除
        """
        if not hwnd or not text:
            return False

        # 激活窗口
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)

        user32.SetForegroundWindow(hwnd)
        time.sleep(0.05)  # 给窗口焦点切换的时间

        # 可选：全选后删除
        if clear_first:
            Sender._send_ctrl_a()
            time.sleep(0.02)
            Sender._send_key(VK_DELETE)
            time.sleep(0.02)

        # 发送文本
        Sender._send_unicode_text(text)

        # 可选：附加 Enter
        if press_enter:
            time.sleep(0.02)
            Sender._send_key(VK_RETURN)

        return True

    @staticmethod
    def send_lines(hwnd, lines, press_enter=True, clear_first=False):
        """
        逐行发送文本（每行后可选加 Enter）

        参数:
            hwnd: 目标窗口句柄
            lines: 文本行列表
            press_enter: 每行后是否附加 Enter
            clear_first: 是否先全选清除
        """
        if not hwnd or not lines:
            return False

        # 激活窗口
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)

        user32.SetForegroundWindow(hwnd)
        time.sleep(0.05)

        if clear_first:
            Sender._send_ctrl_a()
            time.sleep(0.02)
            Sender._send_key(VK_DELETE)
            time.sleep(0.02)

        for i, line in enumerate(lines):
            if line:  # 跳过空行
                Sender._send_unicode_text(line)
            if press_enter:
                time.sleep(0.01)
                Sender._send_key(VK_RETURN)
                time.sleep(0.01)

        return True

    @staticmethod
    def _send_unicode_text(text):
        """使用 KEYEVENTF_UNICODE 发送 Unicode 文本"""
        inputs = []
        extra_info = user32.GetMessageExtraInfo()

        for ch in text:
            code = ord(ch)
            if code == 0:
                continue

            # KEYDOWN
            ki_down = KEYBDINPUT(0, code, KEYEVENTF_UNICODE, 0, extra_info)
            i_down = INPUT(INPUT_KEYBOARD, _INPUT_UNION(ki=ki_down))

            # KEYUP
            ki_up = KEYBDINPUT(0, code, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, extra_info)
            i_up = INPUT(INPUT_KEYBOARD, _INPUT_UNION(ki=ki_up))

            inputs.append(i_down)
            inputs.append(i_up)

        if inputs:
            arr = (INPUT * len(inputs))(*inputs)
            user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))

    @staticmethod
    def _send_key(vk_code):
        """发送单个虚拟键按下+释放"""
        extra_info = user32.GetMessageExtraInfo()

        ki_down = KEYBDINPUT(vk_code, 0, 0, 0, extra_info)
        i_down = INPUT(INPUT_KEYBOARD, _INPUT_UNION(ki=ki_down))

        ki_up = KEYBDINPUT(vk_code, 0, KEYEVENTF_KEYUP, 0, extra_info)
        i_up = INPUT(INPUT_KEYBOARD, _INPUT_UNION(ki=ki_up))

        arr = (INPUT * 2)(i_down, i_up)
        user32.SendInput(2, arr, ctypes.sizeof(INPUT))

    @staticmethod
    def _send_ctrl_a():
        """发送 Ctrl+A"""
        extra_info = user32.GetMessageExtraInfo()

        # Ctrl down
        ki_ctrl = KEYBDINPUT(VK_CONTROL, 0, 0, 0, extra_info)
        i_ctrl = INPUT(INPUT_KEYBOARD, _INPUT_UNION(ki=ki_ctrl))

        # A down
        ki_a = KEYBDINPUT(ord('A'), 0, 0, 0, extra_info)
        i_a = INPUT(INPUT_KEYBOARD, _INPUT_UNION(ki=ki_a))

        # A up
        ki_a_up = KEYBDINPUT(ord('A'), 0, KEYEVENTF_KEYUP, 0, extra_info)
        i_a_up = INPUT(INPUT_KEYBOARD, _INPUT_UNION(ki=ki_a_up))

        # Ctrl up
        ki_ctrl_up = KEYBDINPUT(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0, extra_info)
        i_ctrl_up = INPUT(INPUT_KEYBOARD, _INPUT_UNION(ki=ki_ctrl_up))

        arr = (INPUT * 4)(i_ctrl, i_a, i_a_up, i_ctrl_up)
        user32.SendInput(4, arr, ctypes.sizeof(INPUT))


# ============================================================================
# HighlightOverlay - 拖拽时的窗口高亮
# ============================================================================

class HighlightOverlay:
    """拖拽寻找窗口时，在目标窗口上显示半透明高亮"""

    def __init__(self):
        self.win = None

    def show(self, x, y, w, h):
        """在指定位置显示高亮"""
        if not self.win:
            self.win = tk.Toplevel()
            self.win.overrideredirect(True)
            self.win.attributes("-topmost", True)
            self.win.attributes("-alpha", 0.20)
            self.win.configure(bg="#0078D7")
        self.win.geometry(f"{w}x{h}+{x}+{y}")
        self.win.deiconify()
        self.win.lift()

    def hide(self):
        """隐藏高亮"""
        if self.win:
            self.win.withdraw()

    def destroy(self):
        """销毁高亮窗口"""
        if self.win:
            self.win.destroy()
            self.win = None


# ============================================================================
# DragTarget - 拖拽绑定目标窗口
# ============================================================================

class DragTarget:
    """
    拖拽交互逻辑。
    用户点击 🎯 按钮并拖拽到其他窗口上，松开鼠标后绑定该窗口。
    """

    STATE_IDLE = 0      # 空闲
    STATE_DRAGGING = 1  # 拖拽中

    def __init__(self, app):
        self.app = app
        self.state = self.STATE_IDLE
        self.highlight = HighlightOverlay()
        self.last_hwnd = None

    def start_drag(self, event=None):
        """开始拖拽"""
        if self.state == self.STATE_DRAGGING:
            return
        self.state = self.STATE_DRAGGING
        self.last_hwnd = None
        # 捕获鼠标
        x, y = get_cursor_pos()
        hwnd = window_from_point(x, y)
        user32.SetCapture(hwnd)
        self.app.update_status("拖拽到目标窗口上松开鼠标...")

    def on_mouse_move(self):
        """鼠标移动时，高亮当前窗口"""
        if self.state != self.STATE_DRAGGING:
            return

        x, y = get_cursor_pos()
        hwnd = window_from_point(x, y)

        if hwnd == self.last_hwnd:
            return

        self.last_hwnd = hwnd

        if hwnd and not is_own_window(hwnd):
            try:
                left, top, right, bottom = get_window_rect(hwnd)
                w = right - left
                h = bottom - top
                self.highlight.show(left, top, w, h)
            except Exception:
                self.highlight.hide()
        else:
            self.highlight.hide()

    def end_drag(self, event=None):
        """结束拖拽，绑定窗口"""
        if self.state != self.STATE_DRAGGING:
            return
        self.state = self.STATE_IDLE
        self.highlight.hide()

        user32.ReleaseCapture()

        if self.last_hwnd:
            # 如果目标是自身（本进程的任意窗口），忽略
            if is_own_window(self.last_hwnd):
                self.app.update_status("不能绑定到自身窗口")
                self.last_hwnd = None
                return

            self.app.target_window.bind(self.last_hwnd)
            self.app.update_target_display()
            self.app.update_status(f"已绑定: {self.app.target_window.get_display_text()}")
        else:
            self.app.update_status("未选择目标窗口")

        self.last_hwnd = None

    def cancel_drag(self):
        """取消拖拽"""
        if self.state == self.STATE_DRAGGING:
            self.state = self.STATE_IDLE
            self.highlight.hide()
            user32.ReleaseCapture()
            self.last_hwnd = None
            self.app.update_status("已取消")


# ============================================================================
# LineCanvas - 左侧行号/发送按钮区域
# ============================================================================

class LineCanvas(tk.Canvas):
    """
    左侧画布，实时显示当前行的发送按钮 ▶。
    与 Text 组件同步滚动。
    """

    BTN_WIDTH = 28
    BTN_HEIGHT = 22

    def __init__(self, parent, text_widget, sender_callback, **kwargs):
        kwargs.setdefault("width", self.BTN_WIDTH)
        kwargs.setdefault("highlightthickness", 0)
        kwargs.setdefault("bg", "#f0f0f0")
        super().__init__(parent, **kwargs)
        self.text_widget = text_widget
        self.sender_callback = sender_callback
        self._send_btn = None
        self._current_line = None
        self._after_id = None

        # 创建发送按钮（只创建一次，通过移动位置来跟随光标）
        self._send_btn = tk.Button(
            self,
            text="▶",
            font=("Segoe UI", 9),
            width=3,
            height=1,
            padx=0,
            pady=0,
            bd=1,
            bg="#e8e8e8",
            activebackground="#4CAF50",
            activeforeground="white",
            cursor="hand2",
            command=self._on_send_click,
        )

        # 如果已有 text_widget，立即绑定事件
        if self.text_widget is not None:
            self._bind_events()

        # 初始更新
        self.after(100, self._update_button_position)

    def _bind_events(self):
        """绑定事件到文本组件（text_widget 就绪后调用）"""
        if self.text_widget is None:
            return
        self.text_widget.bind("<KeyRelease>", self._on_cursor_move, add="+")
        self.text_widget.bind("<ButtonRelease>", self._on_cursor_move, add="+")
        self.text_widget.bind("<<Modified>>", self._on_modified, add="+")
        self.text_widget.bind("<MouseWheel>", self._on_text_scroll, add="+")

    def _on_cursor_move(self, event=None):
        """光标移动时更新按钮位置"""
        self._schedule_update()

    def _on_modified(self, event=None):
        """文本修改时更新"""
        if self.text_widget.edit_modified():
            self.text_widget.edit_modified(False)
            self._schedule_update()

    def _on_text_scroll(self, event=None):
        """文本滚动时更新按钮位置"""
        self._schedule_update()

    def _schedule_update(self):
        """延迟更新，避免频繁重绘"""
        if self._after_id:
            self.after_cancel(self._after_id)
        self._after_id = self.after(30, self._update_button_position)

    def _update_button_position(self):
        """更新发送按钮的位置到当前光标行"""
        self._after_id = None
        try:
            text = self.text_widget
            insert_pos = text.index("insert")
            line_num = int(insert_pos.split(".")[0])

            info = text.dlineinfo(insert_pos)
            if info:
                x, y, w, h, baseline = info
                # 更新按钮位置
                btn_y = y + (h - self.BTN_HEIGHT) // 2
                self.coords("send_btn", self.BTN_WIDTH // 2, btn_y + self.BTN_HEIGHT // 2)
                self._current_line = line_num
                self.itemconfigure("send_btn", state="normal")
            else:
                # 行不可见（在可视区域外）
                self.itemconfigure("send_btn", state="hidden")
                self._current_line = None
        except Exception:
            self.itemconfigure("send_btn", state="hidden")
            self._current_line = None

    def _on_send_click(self):
        """点击发送按钮"""
        if self._current_line is not None:
            try:
                line_text = self.text_widget.get(
                    f"{self._current_line}.0",
                    f"{self._current_line}.end"
                )
                if line_text and self.sender_callback:
                    self.sender_callback(line_text)
            except Exception as e:
                print(f"发送失败: {e}")

    def rebuild(self):
        """重建画布内容（切换Tab时调用）"""
        self.delete("all")
        self._current_line = None
        # 重新创建按钮
        self._send_btn = tk.Button(
            self,
            text="▶",
            font=("Segoe UI", 9),
            width=3,
            height=1,
            padx=0,
            pady=0,
            bd=1,
            bg="#e8e8e8",
            activebackground="#4CAF50",
            activeforeground="white",
            cursor="hand2",
            command=self._on_send_click,
        )
        self.create_window(
            self.BTN_WIDTH // 2,
            100,
            window=self._send_btn,
            tags="send_btn",
        )
        self.itemconfigure("send_btn", state="hidden")
        self._schedule_update()

    def destroy(self):
        if self._after_id:
            self.after_cancel(self._after_id)
        super().destroy()


# ============================================================================
# FindDialog - 查找对话框
# ============================================================================

class FindDialog:
    """简单的查找对话框"""

    def __init__(self, parent, text_widget):
        self.parent = parent
        self.text_widget = text_widget
        self.dialog = None
        self.entry = None
        self._search_start = "1.0"

    def show(self):
        """显示查找对话框"""
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.lift()
            self.entry.focus_set()
            self.entry.selection_range(0, "end")
            return

        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("查找")
        self.dialog.geometry("350x120")
        self.dialog.resizable(False, False)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()

        frame = ttk.Frame(self.dialog, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="查找:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.entry = ttk.Entry(frame, width=30)
        self.entry.grid(row=0, column=1, columnspan=2, sticky="ew", padx=(0, 5))
        self.entry.focus_set()

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=1, column=0, columnspan=3, pady=(10, 0))

        ttk.Button(btn_frame, text="查找下一个", command=self._find_next).pack(
            side="left", padx=2
        )
        ttk.Button(btn_frame, text="取消", command=self._close).pack(side="left", padx=2)

        self.dialog.protocol("WM_DELETE_WINDOW", self._close)
        self.entry.bind("<Return>", lambda e: self._find_next())

        frame.columnconfigure(1, weight=1)

    def _find_next(self):
        """查找下一个匹配"""
        search_term = self.entry.get().strip()
        if not search_term:
            return

        text = self.text_widget
        pos = text.search(search_term, self._search_start, "end", nocase=True)
        if pos:
            end_pos = f"{pos}+{len(search_term)}c"
            text.tag_remove("sel", "1.0", "end")
            text.tag_add("sel", pos, end_pos)
            text.see(pos)
            text.mark_set("insert", pos)
            self._search_start = f"{pos}+1c"
            # 高亮
            text.tag_config("sel", background="yellow", foreground="black")
        else:
            # 从头开始找
            self._search_start = "1.0"
            pos = text.search(search_term, self._search_start, "end", nocase=True)
            if pos:
                end_pos = f"{pos}+{len(search_term)}c"
                text.tag_remove("sel", "1.0", "end")
                text.tag_add("sel", pos, end_pos)
                text.see(pos)
                text.mark_set("insert", pos)
                self._search_start = f"{pos}+1c"
            else:
                messagebox.showinfo("查找", f"未找到: {search_term}", parent=self.dialog)

    def _close(self):
        if self.dialog:
            self.dialog.destroy()
            self.dialog = None


# ============================================================================
# EditorTab - 单个标签页编辑器
# ============================================================================

class EditorTab:
    """
    管理一个编辑标签页。
    包含 Text 编辑器 + LineCanvas 行按钮。
    """

    def __init__(self, parent, notebook, app, filepath=None):
        self.app = app
        self.notebook = notebook
        self.filepath = filepath
        self.modified = False

        # 创建标签页内容框架
        self.frame = ttk.Frame(parent)

        # 水平布局：左侧 LineCanvas + 右侧 Text + 滚动条
        self.inner_frame = ttk.Frame(self.frame)
        self.inner_frame.pack(fill="both", expand=True)

        # 左侧画布（行按钮区域）
        self.line_canvas = LineCanvas(
            self.inner_frame, None, self._on_send_line
        )
        self.line_canvas.pack(side="left", fill="y")

        # 右侧编辑区域
        editor_frame = ttk.Frame(self.inner_frame)
        editor_frame.pack(side="left", fill="both", expand=True)

        # 垂直滚动条
        v_scrollbar = ttk.Scrollbar(editor_frame, orient="vertical")
        v_scrollbar.pack(side="right", fill="y")

        # 水平滚动条
        h_scrollbar = ttk.Scrollbar(self.frame, orient="horizontal")
        h_scrollbar.pack(side="bottom", fill="x")

        # 文本编辑器
        self.text = tk.Text(
            editor_frame,
            wrap="none",
            undo=True,
            font=("Consolas", 11),
            padx=8,
            pady=5,
            yscrollcommand=v_scrollbar.set,
            xscrollcommand=h_scrollbar.set,
            selectbackground="#cce8ff",
            inactiveselectbackground="#cce8ff",
        )
        self.text.pack(side="left", fill="both", expand=True)

        # 配置滚动条
        v_scrollbar.config(command=self._on_vertical_scroll)
        h_scrollbar.config(command=self.text.xview)

        # 关联 LineCanvas
        self.line_canvas.text_widget = self.text
        self.line_canvas._bind_events()

        # 绑定事件
        self._bind_events()

        # 如果指定了文件路径，加载内容
        if filepath and os.path.exists(filepath):
            self.load_file(filepath)

        # 确定标题
        self._update_title()

        # 恢复按钮
        self.line_canvas.rebuild()

    def _on_vertical_scroll(self, *args):
        """垂直滚动时同步文本和画布"""
        self.text.yview(*args)
        self.line_canvas._schedule_update()

    def _bind_events(self):
        """绑定编辑器事件"""
        text = self.text

        # 修改标记
        text.bind("<<Modified>>", self._on_modified, add="+")

        # 右键菜单
        text.bind("<Button-3>", self._show_context_menu, add="+")

        # 键盘快捷键 - 由 CmdSenderApp 统一处理

    def _on_modified(self, event=None):
        """文本修改事件"""
        if self.text.edit_modified():
            self.text.edit_modified(False)
            if not self.modified:
                self.modified = True
                self._update_title()

    def _on_send_line(self, line_text):
        """发送当前行"""
        self.app.send_current_line(line_text)

    def _show_context_menu(self, event):
        """显示右键上下文菜单"""
        menu = tk.Menu(self.text, tearoff=0)

        # 检查是否有选中的文本
        has_selection = False
        try:
            has_selection = self.text.tag_ranges("sel") != ()
        except Exception:
            pass

        # 检查是否有绑定窗口
        has_target = self.app.target_window.is_valid()

        if has_selection and has_target:
            menu.add_command(
                label="发送选中行",
                command=self._send_selected_lines,
                accelerator="Shift+F5",
            )
            menu.add_separator()

        if has_target:
            menu.add_command(
                label="发送当前行",
                command=lambda: self._send_current_line(),
                accelerator="F5 / Ctrl+Enter",
            )
            menu.add_separator()

        menu.add_command(
            label="复制",
            command=lambda: self.text.event_generate("<<Copy>>"),
            accelerator="Ctrl+C",
        )
        menu.add_command(
            label="剪切",
            command=lambda: self.text.event_generate("<<Cut>>"),
            accelerator="Ctrl+X",
        )
        menu.add_command(
            label="粘贴",
            command=lambda: self.text.event_generate("<<Paste>>"),
            accelerator="Ctrl+V",
        )
        menu.add_separator()
        menu.add_command(
            label="全选",
            command=lambda: self.text.event_generate("<<SelectAll>>"),
            accelerator="Ctrl+A",
        )

        menu.tk_popup(event.x_root, event.y_root)
        menu.grab_release()

    def _send_current_line(self):
        """发送当前光标所在行"""
        try:
            insert_pos = self.text.index("insert")
            line_num = int(insert_pos.split(".")[0])
            line_text = self.text.get(f"{line_num}.0", f"{line_num}.end")
            if line_text:
                self.app.send_current_line(line_text)
        except Exception as e:
            print(f"发送行失败: {e}")

    def _send_selected_lines(self):
        """发送选中的多行文本"""
        try:
            sel_start = self.text.index("sel.first")
            sel_end = self.text.index("sel.last")
            start_line = int(sel_start.split(".")[0])
            end_line = int(sel_end.split(".")[0])

            lines = []
            for line_num in range(start_line, end_line + 1):
                line_text = self.text.get(f"{line_num}.0", f"{line_num}.end")
                lines.append(line_text)

            if lines:
                self.app.send_multiple_lines(lines)
        except Exception as e:
            print(f"发送选中行失败: {e}")

    def load_file(self, filepath):
        """从文件加载内容"""
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            self.text.delete("1.0", "end")
            self.text.insert("1.0", content)
            self.text.edit_reset()  # 清除撤销历史
            self.text.edit_modified(False)
            self.filepath = filepath
            self.modified = False
            self._update_title()
        except Exception as e:
            messagebox.showerror("打开文件", f"无法打开文件:\n{filepath}\n{e}")

    def save_file(self, filepath=None):
        """保存内容到文件"""
        if filepath:
            self.filepath = filepath

        if not self.filepath:
            return False

        try:
            content = self.text.get("1.0", "end-1c")
            with open(self.filepath, "w", encoding="utf-8") as f:
                f.write(content)
            self.text.edit_modified(False)
            self.modified = False
            self._update_title()
            return True
        except Exception as e:
            messagebox.showerror("保存文件", f"无法保存文件:\n{self.filepath}\n{e}")
            return False

    def _update_title(self):
        """更新标签页标题"""
        if self.filepath:
            basename = os.path.basename(self.filepath)
        else:
            basename = "未命名"

        if self.modified:
            title = f"* {basename}"
        else:
            title = basename

        # 更新 Notebook 标签
        for i in range(self.notebook.index("end")):
            if self.notebook.nametowidget(self.notebook.tabs()[i]) == self.frame:
                self.notebook.tab(i, text=title)
                break

    def focus(self):
        """获取焦点"""
        self.text.focus_set()


# ============================================================================
# FileManager - 文件管理
# ============================================================================

class FileManager:
    """文件的打开、保存、新建操作"""

    def __init__(self, app):
        self.app = app
        # 上次使用的目录
        self.last_dir = os.path.expanduser("~")

    def new_file(self):
        """新建文件"""
        self.app.create_new_tab()

    def open_file(self):
        """打开文件"""
        filepath = filedialog.askopenfilename(
            title="打开文件",
            initialdir=self.last_dir,
            filetypes=[
                ("文本文件", "*.txt *.cmd *.bat *.ps1 *.py *.js *.html *.css *.json *.xml *.md *.log *.ini *.cfg *.yaml *.yml *.toml *.csv"),
                ("所有文件", "*.*"),
            ],
        )
        if filepath:
            self.last_dir = os.path.dirname(filepath)
            self.app.create_new_tab(filepath=filepath)

    def save_file(self):
        """保存当前文件"""
        current = self.app.get_current_tab()
        if not current:
            return False

        if current.filepath:
            return current.save_file()
        else:
            return self.save_file_as()

    def save_file_as(self):
        """另存为"""
        current = self.app.get_current_tab()
        if not current:
            return False

        filepath = filedialog.asksaveasfilename(
            title="另存为",
            initialdir=self.last_dir,
            initialfile=os.path.basename(current.filepath) if current.filepath else "未命名.txt",
            defaultextension=".txt",
            filetypes=[
                ("文本文件", "*.txt"),
                ("所有文件", "*.*"),
            ],
        )
        if filepath:
            self.last_dir = os.path.dirname(filepath)
            return current.save_file(filepath)
        return False


# ============================================================================
# CmdSenderApp - 主应用程序
# ============================================================================

class CmdSenderApp(tk.Tk):
    """
    主窗口，管理菜单、工具栏、Notebook 标签页。
    """

    def __init__(self):
        super().__init__()

        self.title("cmd_sender - 命令发送器")
        self.geometry("900x650")
        self.minsize(600, 400)

        # 设置图标（如果有）
        try:
            self.iconbitmap(default="")
        except Exception:
            pass

        # 核心组件
        self.target_window = TargetWindow()
        self.sender = Sender()
        self.drag_target = DragTarget(self)
        self.file_manager = FileManager(self)

        # 标签页管理
        self.tabs = []  # EditorTab 列表
        self._current_tab_index = -1

        # 设置选项
        self.auto_enter = tk.BooleanVar(value=True)
        self.clear_first = tk.BooleanVar(value=False)

        # 构建 UI
        self._build_menu()
        self._build_toolbar()
        self._build_notebook()
        self._build_statusbar()

        # 绑定全局快捷键
        self._bind_shortcuts()

        # 拖拽跟踪定时器
        self._drag_timer_id = None
        self._start_drag_tracking()

        # 创建一个默认空标签页
        self.create_new_tab()

        # 窗口关闭处理
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- UI 构建 ----

    def _build_menu(self):
        """构建菜单栏"""
        menubar = tk.Menu(self)

        # File 菜单
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="新建", command=self.file_manager.new_file, accelerator="Ctrl+N")
        file_menu.add_command(label="打开", command=self.file_manager.open_file, accelerator="Ctrl+O")
        file_menu.add_command(label="保存", command=self.file_manager.save_file, accelerator="Ctrl+S")
        file_menu.add_command(label="另存为", command=self.file_manager.save_file_as, accelerator="Ctrl+Shift+S")
        file_menu.add_separator()
        file_menu.add_command(label="关闭标签", command=self._close_current_tab, accelerator="Ctrl+W")
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self._on_close, accelerator="Alt+F4")
        menubar.add_cascade(label="文件", menu=file_menu)

        # Edit 菜单
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="撤销", command=self._undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="重做", command=self._redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="剪切", command=self._cut, accelerator="Ctrl+X")
        edit_menu.add_command(label="复制", command=self._copy, accelerator="Ctrl+C")
        edit_menu.add_command(label="粘贴", command=self._paste, accelerator="Ctrl+V")
        edit_menu.add_separator()
        edit_menu.add_command(label="查找", command=self._find, accelerator="Ctrl+F")
        edit_menu.add_separator()
        edit_menu.add_command(label="全选", command=self._select_all, accelerator="Ctrl+A")
        menubar.add_cascade(label="编辑", menu=edit_menu)

        # 发送 菜单
        send_menu = tk.Menu(menubar, tearoff=0)
        send_menu.add_command(label="发送当前行", command=self._menu_send_current_line, accelerator="F5")
        send_menu.add_command(label="发送选中行", command=self._menu_send_selected, accelerator="Shift+F5")
        send_menu.add_separator()
        send_menu.add_checkbutton(label="发送后附加回车", variable=self.auto_enter)
        send_menu.add_checkbutton(label="发送前清空 (Ctrl+A)", variable=self.clear_first)
        send_menu.add_separator()
        send_menu.add_command(label="解除窗口绑定", command=self._unbind_target)
        menubar.add_cascade(label="发送", menu=send_menu)

        self.config(menu=menubar)

    def _build_toolbar(self):
        """构建工具栏"""
        toolbar = ttk.Frame(self, padding=(5, 2))
        toolbar.pack(side="top", fill="x")

        # 🎯 拖拽绑定按钮
        self.drag_btn = tk.Button(
            toolbar,
            text="🎯",
            font=("Segoe UI", 16),
            width=3,
            height=1,
            bd=1,
            bg="#f0f0f0",
            activebackground="#e0e0e0",
            cursor="crosshair",
            relief="raised",
        )
        self.drag_btn.pack(side="left", padx=(0, 5))
        self.drag_btn.bind("<ButtonPress-1>", self._on_drag_start)

        # 目标窗口显示
        self.target_label = ttk.Label(
            toolbar, text="🎯 目标: 未绑定窗口", font=("Segoe UI", 10)
        )
        self.target_label.pack(side="left", padx=(5, 20))

        # 分隔符
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=5)

        # 发送选项
        self.enter_chk = ttk.Checkbutton(
            toolbar, text="⏎ 回车", variable=self.auto_enter
        )
        self.enter_chk.pack(side="left", padx=2)

        self.clear_chk = ttk.Checkbutton(
            toolbar, text="清空", variable=self.clear_first
        )
        self.clear_chk.pack(side="left", padx=2)

        # 右侧填充
        ttk.Label(toolbar, text="").pack(side="left", fill="x", expand=True)

        # 发送按钮（大）
        self.send_btn = ttk.Button(
            toolbar,
            text="▶ 发送当前行",
            command=self._menu_send_current_line,
        )
        self.send_btn.pack(side="right", padx=2)

        self.send_sel_btn = ttk.Button(
            toolbar,
            text="▶▶ 发送选中行",
            command=self._menu_send_selected,
        )
        self.send_sel_btn.pack(side="right", padx=2)

    def _build_notebook(self):
        """构建 Notebook (多标签编辑器)"""
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(side="top", fill="both", expand=True, padx=2, pady=(0, 2))

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _build_statusbar(self):
        """构建状态栏"""
        self.status_var = tk.StringVar(value="就绪")
        statusbar = ttk.Label(
            self,
            textvariable=self.status_var,
            relief="sunken",
            anchor="w",
            padding=(5, 2),
        )
        statusbar.pack(side="bottom", fill="x")

    # ---- 快捷键绑定 ----

    def _bind_shortcuts(self):
        """绑定键盘快捷键"""
        self.bind_all("<Control-n>", lambda e: self.file_manager.new_file())
        self.bind_all("<Control-N>", lambda e: self.file_manager.new_file())
        self.bind_all("<Control-o>", lambda e: self.file_manager.open_file())
        self.bind_all("<Control-O>", lambda e: self.file_manager.open_file())
        self.bind_all("<Control-s>", lambda e: self.file_manager.save_file())
        self.bind_all("<Control-S>", lambda e: self.file_manager.save_file())
        self.bind_all("<Control-Shift-S>", lambda e: self.file_manager.save_file_as())
        self.bind_all("<Control-Shift-s>", lambda e: self.file_manager.save_file_as())
        self.bind_all("<Control-w>", lambda e: self._close_current_tab())
        self.bind_all("<Control-W>", lambda e: self._close_current_tab())
        self.bind_all("<Control-f>", lambda e: self._find())
        self.bind_all("<Control-F>", lambda e: self._find())
        self.bind_all("<F5>", lambda e: self._menu_send_current_line())
        self.bind_all("<Control-Return>", lambda e: self._menu_send_current_line())
        self.bind_all("<Control-KP_Enter>", lambda e: self._menu_send_current_line())
        self.bind_all("<Shift-F5>", lambda e: self._menu_send_selected())

    # ---- 标签页管理 ----

    def create_new_tab(self, filepath=None):
        """创建新的编辑标签页"""
        tab = EditorTab(self.notebook, self.notebook, self, filepath=filepath)
        self.notebook.add(tab.frame, text="未命名")

        self.tabs.append(tab)

        # 切换到新标签
        self.notebook.select(tab.frame)
        self._current_tab_index = len(self.tabs) - 1

        tab.focus()
        self.update_status(f"新建标签: {tab.notebook.tab(tab.frame, 'text')}")
        return tab

    def get_current_tab(self):
        """获取当前活动的标签页"""
        if not self.tabs:
            return None
        try:
            selected = self.notebook.select()
            if not selected:
                return None
            frame = self.notebook.nametowidget(selected)
            for tab in self.tabs:
                if tab.frame == frame:
                    return tab
        except Exception:
            pass
        return None

    def _on_tab_changed(self, event):
        """标签切换事件"""
        for i, tab in enumerate(self.tabs):
            if tab.frame == self.notebook.nametowidget(self.notebook.select()):
                self._current_tab_index = i
                tab.line_canvas._schedule_update()
                break

    def _close_current_tab(self):
        """关闭当前标签"""
        tab = self.get_current_tab()
        if not tab:
            return

        if tab.modified:
            # 显示保存提示
            title = tab.notebook.tab(tab.frame, "text")
            result = messagebox.askyesnocancel(
                "保存确认",
                f"是否保存 '{title}' 的更改？",
                default=messagebox.YES,
            )
            if result is None:  # 取消
                return
            if result:  # 是
                if not self.file_manager.save_file():
                    return  # 保存失败则取消关闭

        # 关闭标签
        tab.line_canvas.destroy()
        self.notebook.forget(tab.frame)
        tab.frame.destroy()
        self.tabs.remove(tab)

        # 如果没有标签了，创建一个新标签
        if not self.tabs:
            self.create_new_tab()

        self.update_status("已关闭标签")

    # ---- 拖拽绑定 ----

    def _on_drag_start(self, event):
        """拖拽开始"""
        self.drag_target.start_drag(event)

    def _start_drag_tracking(self):
        """启动拖拽跟踪定时器"""
        if self.drag_target.state == DragTarget.STATE_DRAGGING:
            self.drag_target.on_mouse_move()
        self._drag_timer_id = self.after(50, self._start_drag_tracking)

    def _on_drag_mouse_up(self, event):
        """鼠标释放（全局）"""
        if self.drag_target.state == DragTarget.STATE_DRAGGING:
            self.drag_target.end_drag(event)

    # ---- 发送操作 ----

    def send_current_line(self, line_text):
        """发送当前行"""
        if not line_text:
            self.update_status("没有可发送的内容")
            return

        if not self.target_window.is_valid():
            self.update_status("未绑定目标窗口，请先点击 🎯 拖拽到目标窗口")
            messagebox.showwarning("未绑定窗口", "请先点击工具栏的 🎯 按钮，拖拽到目标窗口上绑定。")
            return

        self.update_status(f"发送: {line_text[:50]}{'...' if len(line_text) > 50 else ''}")
        self.sender.send_text(
            self.target_window.hwnd,
            line_text,
            press_enter=self.auto_enter.get(),
            clear_first=self.clear_first.get(),
        )

    def send_multiple_lines(self, lines):
        """发送多行"""
        if not lines:
            self.update_status("没有可发送的内容")
            return

        if not self.target_window.is_valid():
            self.update_status("未绑定目标窗口")
            messagebox.showwarning("未绑定窗口", "请先点击工具栏的 🎯 按钮，拖拽到目标窗口上绑定。")
            return

        text = "\n".join(lines)
        self.update_status(f"发送 {len(lines)} 行: {text[:50]}{'...' if len(text) > 50 else ''}")
        self.sender.send_lines(
            self.target_window.hwnd,
            lines,
            press_enter=self.auto_enter.get(),
            clear_first=self.clear_first.get(),
        )

    def _menu_send_current_line(self):
        """菜单/快捷键触发发送当前行"""
        tab = self.get_current_tab()
        if tab:
            tab._send_current_line()

    def _menu_send_selected(self):
        """菜单/快捷键触发发送选中行"""
        tab = self.get_current_tab()
        if tab:
            tab._send_selected_lines()

    def _unbind_target(self):
        """解除窗口绑定"""
        self.target_window.clear()
        self.update_target_display()
        self.update_status("已解除窗口绑定")

    # ---- 编辑操作 ----

    def _undo(self):
        tab = self.get_current_tab()
        if tab:
            try:
                tab.text.edit_undo()
            except tk.TclError:
                pass

    def _redo(self):
        tab = self.get_current_tab()
        if tab:
            try:
                tab.text.edit_redo()
            except tk.TclError:
                pass

    def _cut(self):
        tab = self.get_current_tab()
        if tab:
            tab.text.event_generate("<<Cut>>")

    def _copy(self):
        tab = self.get_current_tab()
        if tab:
            tab.text.event_generate("<<Copy>>")

    def _paste(self):
        tab = self.get_current_tab()
        if tab:
            tab.text.event_generate("<<Paste>>")

    def _select_all(self):
        tab = self.get_current_tab()
        if tab:
            tab.text.tag_add("sel", "1.0", "end")

    def _find(self):
        """打开查找对话框"""
        tab = self.get_current_tab()
        if tab:
            if not hasattr(self, "_find_dialog") or not self._find_dialog:
                self._find_dialog = FindDialog(self, tab.text)
            else:
                self._find_dialog.text_widget = tab.text
            self._find_dialog.show()

    # ---- 界面更新 ----

    def update_target_display(self):
        """更新目标窗口显示"""
        if self.target_window.is_valid():
            text = f"🎯 {self.target_window.get_display_text()}"
            self.target_label.config(text=text)
            self.drag_btn.config(bg="#d4edda")  # 绿色提示已绑定
        else:
            self.target_label.config(text="🎯 目标: 未绑定窗口")
            self.drag_btn.config(bg="#f0f0f0")

    def update_status(self, message):
        """更新状态栏"""
        self.status_var.set(message)

    # ---- 窗口关闭 ----

    def _on_close(self):
        """关闭窗口"""
        # 检查所有标签是否有未保存的更改
        for tab in self.tabs[:]:
            if tab.modified:
                self.notebook.select(tab.frame)
                title = tab.notebook.tab(tab.frame, "text")
                result = messagebox.askyesnocancel(
                    "保存确认",
                    f"是否保存 '{title}' 的更改？",
                    default=messagebox.YES,
                )
                if result is None:  # 取消退出
                    return
                if result:  # 是
                    if not self.file_manager.save_file():
                        return

        # 清理拖拽资源
        self.drag_target.cancel_drag()
        self.drag_target.highlight.destroy()
        if self._drag_timer_id:
            self.after_cancel(self._drag_timer_id)

        self.destroy()

    def run(self):
        """运行应用"""
        self.mainloop()


# ============================================================================
# 全局鼠标事件钩子
# ============================================================================

class GlobalMouseTracker:
    """全局鼠标事件跟踪，用于捕获鼠标释放事件"""

    def __init__(self, app):
        self.app = app
        self._binding_id = None

    def install(self):
        """安装全局鼠标事件监听"""
        self._binding_id = self.app.bind_all(
            "<ButtonRelease-1>", self._on_button_release
        )

    def _on_button_release(self, event):
        """鼠标释放事件"""
        self.app._on_drag_mouse_up(event)

    def uninstall(self):
        """卸载"""
        if self._binding_id:
            try:
                self.app.unbind_all("<ButtonRelease-1>")
            except tk.TclError:
                pass  # 窗口已销毁，忽略


# ============================================================================
# 程序入口
# ============================================================================

def main():
    """程序入口函数"""
    # 检查是否在 Windows 环境下运行
    if sys.platform != "win32":
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "不支持的操作系统",
            "cmd_sender 仅在 Windows 下运行。\n"
            "请使用 Windows 10/11 + Python 3.10+。",
        )
        root.destroy()
        sys.exit(1)

    app = CmdSenderApp()

    # 安装全局鼠标事件
    tracker = GlobalMouseTracker(app)
    tracker.install()

    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        tracker.uninstall()


if __name__ == "__main__":
    main()

