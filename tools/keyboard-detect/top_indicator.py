"""
方案 A：屏幕顶端极细发光指示条 (Top Edge Glow Line - Bloom Edition)
根据原型图设计：屏幕顶部居中 1/4 宽度，2px 极细核心亮线，四周带平滑发光/泛光 (Glow) 与两端渐变收尾。

核心特性：
- 居中 1/4 屏幕宽度（默认 2560 屏对应 640px 核心宽，两侧平滑衰减渐变过渡）
- 2px 极细实体亮线（与屏幕上边框贴合）+ 12px 柔和垂直泛光晕染
- 基于 Windows 32 位 DIB 与 UpdateLayeredWindow (AC_SRC_ALPHA) 硬件加速实时 Alpha 混色合成
- 100% 鼠标穿透 (WS_EX_TRANSPARENT + WM_NCHITTEST 返回 HTTRANSPARENT)
- 显式绑定 Windows 用户物理交互桌面 (Default)
- 支持单屏及多显示器扩展模式自适应
- 硬件事件 (WM_DEVICECHANGE) + 300ms 心跳双通道监听
"""

import sys
import os
import time
import math
import argparse
import subprocess
import ctypes
from ctypes import wintypes

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

# 在 pythonw.exe 无控制台环境下静默重定向 stdout/stderr
if sys.stdout is None:
    try:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass
if sys.stderr is None:
    try:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    except Exception:
        pass

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

LOG_FILE = os.path.join(SCRIPT_DIR, "runtime.log")

def log_debug(msg):
    try:
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        pid = os.getpid()
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{now}] [PID:{pid}] {msg}\n")
    except Exception:
        pass

from detect_keyboard import check_status

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000

WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000

HWND_TOPMOST = wintypes.HWND(-1)
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_SHOWWINDOW = 0x0040

SW_HIDE = 0
SW_SHOWNOACTIVATE = 4
SW_SHOWNA = 8

HTTRANSPARENT = -1

WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_NCHITTEST = 0x0084
WM_TIMER = 0x0113
WM_DISPLAYCHANGE = 0x007E
WM_DEVICECHANGE = 0x0219

CLASS_NAME = "KeyboardTopGlow_Indicator_Overlay_V2"
MUTEX_NAME = "Local\\KeyboardTopGlow_Indicator_Mutex_V2"

class POINT(ctypes.Structure):
    _fields_ = [('x', wintypes.LONG), ('y', wintypes.LONG)]

class SIZE(ctypes.Structure):
    _fields_ = [('cx', wintypes.LONG), ('cy', wintypes.LONG)]

class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ('BlendOp', wintypes.BYTE),
        ('BlendFlags', wintypes.BYTE),
        ('SourceConstantAlpha', wintypes.BYTE),
        ('AlphaFormat', wintypes.BYTE)
    ]

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', wintypes.DWORD),
        ('biWidth', wintypes.LONG),
        ('biHeight', wintypes.LONG),
        ('biPlanes', wintypes.WORD),
        ('biBitCount', wintypes.WORD),
        ('biCompression', wintypes.DWORD),
        ('biSizeImage', wintypes.DWORD),
        ('biXPelsPerMeter', wintypes.LONG),
        ('biYPelsPerMeter', wintypes.LONG),
        ('biClrUsed', wintypes.DWORD),
        ('biClrImportant', wintypes.DWORD),
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ('bmiHeader', BITMAPINFOHEADER),
        ('bmiColors', wintypes.DWORD * 3)
    ]

class RECT(ctypes.Structure):
    _fields_ = [
        ('left', wintypes.LONG),
        ('top', wintypes.LONG),
        ('right', wintypes.LONG),
        ('bottom', wintypes.LONG),
    ]

class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('rcMonitor', RECT),
        ('rcWork', RECT),
        ('dwFlags', wintypes.DWORD),
    ]

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = ctypes.c_longlong

user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID
]
user32.CreateWindowExW.restype = wintypes.HWND

user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.UINT
]
user32.SetWindowPos.restype = wintypes.BOOL

user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL

user32.UpdateLayeredWindow.argtypes = [
    wintypes.HWND, wintypes.HDC,
    ctypes.POINTER(POINT), ctypes.POINTER(SIZE),
    wintypes.HDC, ctypes.POINTER(POINT),
    wintypes.COLORREF, ctypes.POINTER(BLENDFUNCTION),
    wintypes.DWORD
]
user32.UpdateLayeredWindow.restype = wintypes.BOOL

class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.UINT),
        ('style', wintypes.UINT),
        ('lpfnWndProc', WNDPROC),
        ('cbClsExtra', ctypes.c_int),
        ('cbWndExtra', ctypes.c_int),
        ('hInstance', wintypes.HINSTANCE),
        ('hIcon', wintypes.HICON),
        ('hCursor', wintypes.HANDLE),
        ('hbrBackground', wintypes.HBRUSH),
        ('lpszMenuName', wintypes.LPCWSTR),
        ('lpszClassName', wintypes.LPCWSTR),
        ('hIconSm', wintypes.HICON)
    ]

MONITORENUMPROC = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HANDLE,
    wintypes.HDC,
    ctypes.POINTER(RECT),
    wintypes.LPARAM
)

def enumerate_monitors():
    monitors = []
    def _callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hMonitor, ctypes.byref(info)):
            rc = info.rcMonitor
            monitors.append({
                'left': rc.left,
                'top': rc.top,
                'right': rc.right,
                'bottom': rc.bottom,
                'width': rc.right - rc.left,
                'height': rc.bottom - rc.top,
                'is_primary': bool(info.dwFlags & 1)
            })
        return True

    cb = MONITORENUMPROC(_callback)
    user32.EnumDisplayMonitors(None, None, cb, 0)
    
    if not monitors:
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        monitors.append({
            'left': 0, 'top': 0, 'right': w, 'bottom': h,
            'width': w, 'height': h, 'is_primary': True
        })
    return monitors

def generate_glow_bitmap_data(width, height, core_w, core_h, fade_x, fade_y, base_color):
    """
    生成 32 位预乘 Alpha (Premultiplied ARGB) 字节数组。
    精确复刻 proto_top_line.jpg 的视觉效果：
    - 顶部贴边 2px 极细高光核心（微白亮青色）
    - 向下垂直发散 12px 柔和泛光晕染
    - 左右两侧采用余弦平滑过渡逐渐淡出至完全透明
    """
    pixels = bytearray(width * height * 4)
    r_base, g_base, b_base = base_color
    half_w = core_w / 2.0
    center_x = width / 2.0

    for y in range(height):
        if y < core_h:
            iy = 1.0
            ay = 0.98  # 核心实线的高不透明度
        else:
            dy = y - core_h + 1
            ratio = dy / max(1, fade_y)
            if ratio > 1.0:
                iy = 0.0
                ay = 0.0
            else:
                # 柔和的幂次泛光衰减曲线
                iy = (1.0 - ratio) ** 1.5
                ay = 0.75 * ((1.0 - ratio) ** 2.2)

        for x in range(width):
            dx = abs(x - center_x)
            if dx <= half_w - fade_x:
                ix = 1.0
            elif dx <= half_w + fade_x:
                t = (dx - (half_w - fade_x)) / (2.0 * fade_x)
                ix = 0.5 * (1.0 + math.cos(math.pi * t))
            else:
                ix = 0.0

            alpha = ay * ix
            if alpha <= 0.001:
                continue

            # 核心区白热化混色 (White-Hot Core)，外圈呈现纯净青蓝霓虹光
            core_factor = iy * ix
            r = int(r_base * (1.0 - core_factor * 0.7) + 255 * (core_factor * 0.7))
            g = int(g_base * (1.0 - core_factor * 0.35) + 255 * (core_factor * 0.35))
            b = int(b_base * (1.0 - core_factor * 0.15) + 255 * (core_factor * 0.15))

            r = min(255, max(0, r))
            g = min(255, max(0, g))
            b = min(255, max(0, b))

            # Windows DIB 预乘 Alpha (Premultiplied ARGB: B, G, R, A)
            idx = (y * width + x) * 4
            pixels[idx + 0] = int(b * alpha)
            pixels[idx + 1] = int(g * alpha)
            pixels[idx + 2] = int(r * alpha)
            pixels[idx + 3] = int(255 * alpha)

    return bytes(pixels)

class IndicatorApp:
    def __init__(self, width_ratio=0.25, height=2, glow=12, fade_x=45, color=(0, 229, 255), primary_only=False, heartbeat_interval=300):
        self.width_ratio = max(0.05, min(1.0, width_ratio))
        self.core_h = max(1, height)
        self.glow_y = max(4, glow)
        self.fade_x = max(10, fade_x)
        self.color = color  # (R, G, B)
        self.primary_only = primary_only
        self.heartbeat_interval = heartbeat_interval

        self.hinstance = kernel32.GetModuleHandleW(None)
        self.class_name = CLASS_NAME
        self.class_atom = None
        self.wndproc = None
        
        # 维护每个显示器的窗口句柄与 DIB 资源
        self.window_entries = []
        self.is_connected = None
        self.mutex = None

    def ensure_interactive_desktop(self):
        """显式绑定至当前交互用户的 Default 桌面，防止后台会话/沙箱隔离导致窗口隐藏"""
        try:
            hDesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
            if hDesk:
                user32.SetThreadDesktop(hDesk)
                log_debug("成功绑定至用户物理交互桌面 'Default'")
        except Exception as e:
            log_debug(f"绑定交互桌面异常: {e}")

    def wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == WM_NCHITTEST:
            return HTTRANSPARENT

        elif msg == WM_DEVICECHANGE:
            self.refresh_keyboard_status("硬件插拔事件 (WM_DEVICECHANGE)")
            return 0

        elif msg == WM_TIMER:
            self.refresh_keyboard_status("心跳检测")
            return 0

        elif msg == WM_DISPLAYCHANGE:
            self.create_indicator_windows()
            self.is_connected = None
            self.refresh_keyboard_status("显示器变更重刷")
            return 0

        elif msg == WM_CLOSE:
            user32.DestroyWindow(hwnd)
            return 0

        elif msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0

        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def refresh_keyboard_status(self, trigger_reason=""):
        try:
            status = check_status()
            now_connected = status["connected"]

            if now_connected != self.is_connected:
                self.is_connected = now_connected
                now_str = time.strftime('%H:%M:%S')

                if self.is_connected:
                    kb_names = ", ".join(status["keyboard_names"]) or "外接键盘"
                    log_debug(f"键盘已接入本机 ({kb_names}) -> 点亮屏幕顶端发光条 [ON]")
                    print(f"[{now_str}] 键盘已接入本机 ({kb_names}) -> 点亮屏幕顶端发光条 [ON]")
                    for entry in self.window_entries:
                        hwnd = entry['hwnd']
                        user32.ShowWindow(hwnd, SW_SHOWNA)
                        user32.SetWindowPos(
                            hwnd, HWND_TOPMOST,
                            0, 0, 0, 0,
                            SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_SHOWWINDOW
                        )
                else:
                    log_debug(f"键盘已断开 -> 熄灭屏幕顶端光条 [OFF]")
                    print(f"[{now_str}] 键盘已断开（切换至另一台电脑） -> 熄灭屏幕顶端光条 [OFF]")
                    for entry in self.window_entries:
                        user32.ShowWindow(entry['hwnd'], SW_HIDE)
        except Exception as e:
            log_debug(f"检测状态异常: {e}")
            print(f"检测状态异常: {e}")

    def create_indicator_windows(self):
        # 清理旧窗口及 GDI 资源
        for entry in self.window_entries:
            try:
                user32.DestroyWindow(entry['hwnd'])
                gdi32.DeleteObject(entry['hbm'])
                gdi32.DeleteDC(entry['hdc_mem'])
            except Exception:
                pass
        self.window_entries.clear()

        monitors = enumerate_monitors()
        if self.primary_only:
            monitors = [m for m in monitors if m['is_primary']] or monitors[:1]

        ex_style = WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_LAYERED | WS_EX_TRANSPARENT
        style = WS_POPUP

        hdc_screen = user32.GetDC(0)

        for idx, m in enumerate(monitors, 1):
            m_w = m['width']
            m_left = m['left']
            m_top = m['top']

            # 计算居中 1/4 宽度与泛光边界
            core_w = int(m_w * self.width_ratio)
            win_w = core_w + 2 * self.fade_x
            win_h = self.core_h + self.glow_y
            win_x = m_left + (m_w - win_w) // 2
            win_y = m_top

            hwnd = user32.CreateWindowExW(
                ex_style,
                self.class_name,
                f"TopGlowIndicator_{idx}",
                style,
                win_x, win_y, win_w, win_h,
                None, None, self.hinstance, None
            )
            if not hwnd:
                log_debug(f"CreateWindowExW [Monitor {idx}] 失败: {kernel32.GetLastError()}")
                continue

            # 创建 32 位 DIB 与内存 DC
            hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
            bmi = BITMAPINFO()
            bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.bmiHeader.biWidth = win_w
            bmi.bmiHeader.biHeight = -win_h  # 负高表示从上向下的 Top-down DIB
            bmi.bmiHeader.biPlanes = 1
            bmi.bmiHeader.biBitCount = 32
            bmi.bmiHeader.biCompression = 0

            ppv_bits = ctypes.c_void_p()
            hbm = gdi32.CreateDIBSection(hdc_mem, ctypes.byref(bmi), 0, ctypes.byref(ppv_bits), None, 0)
            gdi32.SelectObject(hdc_mem, hbm)

            # 生成并写入预乘 Alpha 泛光位图
            pixel_bytes = generate_glow_bitmap_data(
                win_w, win_h, core_w, self.core_h, self.fade_x, self.glow_y, self.color
            )
            ctypes.memmove(ppv_bits, pixel_bytes, len(pixel_bytes))

            # 调用 UpdateLayeredWindow 完成硬件加速混色合成设置
            pt_dest = POINT(win_x, win_y)
            sz = SIZE(win_w, win_h)
            pt_src = POINT(0, 0)
            blend = BLENDFUNCTION(0, 0, 255, 1)  # AC_SRC_OVER, AC_SRC_ALPHA

            user32.UpdateLayeredWindow(
                hwnd, hdc_screen,
                ctypes.byref(pt_dest), ctypes.byref(sz),
                hdc_mem, ctypes.byref(pt_src),
                0, ctypes.byref(blend), 2  # ULW_ALPHA
            )

            log_debug(f"创建发光条 [Monitor {idx}] 居中范围 ({win_x},{win_y},{win_w},{win_h}) 核心宽 {core_w}px -> HWND: {hwnd}")
            self.window_entries.append({
                'hwnd': hwnd,
                'hdc_mem': hdc_mem,
                'hbm': hbm,
                'win_x': win_x,
                'win_y': win_y,
                'win_w': win_w,
                'win_h': win_h
            })

        user32.ReleaseDC(0, hdc_screen)

        if self.window_entries:
            user32.SetTimer(self.window_entries[0]['hwnd'], 1001, self.heartbeat_interval, None)

    def setup(self):
        # 1. 显式接入真实物理屏幕桌面
        self.ensure_interactive_desktop()

        # 2. DPI 感知
        try:
            user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            pass

        # 3. 互斥体单实例检测
        self.mutex = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        if kernel32.GetLastError() == 183:
            print("[提示] 键盘指示条已经在后台运行中，无需重复启动。")
            sys.exit(0)

        # 4. 注册透明层叠窗口类
        self.wndproc = WNDPROC(self.wnd_proc)
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.style = 0
        wc.lpfnWndProc = self.wndproc
        wc.hInstance = self.hinstance
        wc.hCursor = None
        wc.hbrBackground = None  # 层叠窗口由 UpdateLayeredWindow 完全托管
        wc.lpszClassName = self.class_name

        self.class_atom = user32.RegisterClassExW(ctypes.byref(wc))
        if not self.class_atom:
            raise RuntimeError(f"注册窗口类失败，错误码: {kernel32.GetLastError()}")

        self.create_indicator_windows()

        print("=" * 65)
        print("【方案 A：屏幕顶端发光指示条 (Bloom Edition) 已就绪】")
        print(f"宽度比例: {int(self.width_ratio * 100)}% 居中 | 核心高度: {self.core_h}px | 泛光高度: {self.glow_y}px")
        print(f"发光颜色: RGB{self.color} (带两端平滑渐变收尾)")
        print("鼠标穿透: 已开启 (WS_EX_TRANSPARENT + HTTRANSPARENT 100% 完全穿透)")
        print(f"监控模式: {self.heartbeat_interval}ms 心跳 + WM_DEVICECHANGE 双通道")
        print("按 Ctrl+C 可退出。")
        print("=" * 65)

        self.refresh_keyboard_status("初始启动检测")

    def run(self):
        self.setup()
        msg = wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            self.cleanup()

    def cleanup(self):
        if self.window_entries:
            try:
                user32.KillTimer(self.window_entries[0]['hwnd'], 1001)
            except Exception:
                pass
            for entry in self.window_entries:
                try:
                    user32.DestroyWindow(entry['hwnd'])
                    gdi32.DeleteObject(entry['hbm'])
                    gdi32.DeleteDC(entry['hdc_mem'])
                except Exception:
                    pass
            self.window_entries.clear()

        if self.class_atom:
            user32.UnregisterClassW(self.class_name, self.hinstance)
            self.class_atom = None

        if self.mutex:
            kernel32.CloseHandle(self.mutex)
            self.mutex = None

        print("\n指示条已正常退出，资源已释放。")

def stop_running_instance():
    try:
        user32.SetThreadDesktop(user32.OpenDesktopW("Default", 0, False, 0x01FF))
    except Exception:
        pass

    stopped = False
    hwnd = user32.FindWindowW(CLASS_NAME, None)
    while hwnd:
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        stopped = True
        hwnd = user32.FindWindowExW(None, hwnd, CLASS_NAME, None)

    try:
        current_pid = os.getpid()
        ps_cmd = f"powershell -NoProfile -ExecutionPolicy Bypass -Command \"Get-Process python*, pythonw* -ErrorAction SilentlyContinue | Where-Object Id -ne {current_pid} | ForEach-Object {{ try {{ $cmd = (Get-CimInstance Win32_Process -Filter \\\"ProcessId = $($_.Id)\\\").CommandLine; if ($cmd -match 'top_indicator\\.py') {{ Stop-Process -Id $_.Id -Force }} }} catch {{}} }}\""
        subprocess.run(ps_cmd, shell=True, capture_output=True)
        stopped = True
    except Exception:
        pass

    if stopped:
        print("============================================================")
        print("【成功】已停止后台键盘指示条进程。")
        print("============================================================")
    else:
        print("[提示] 未发现正在运行的指示条进程。")

def parse_color(hex_str):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    return (0, 229, 255)

def main():
    parser = argparse.ArgumentParser(description="屏幕顶端发光指示条 (Bloom Edition)")
    parser.add_argument("--width-ratio", type=float, default=0.25, help="宽度占屏幕比例，默认 0.25 (即 1/4 居中)")
    parser.add_argument("--height", type=int, default=2, help="核心实线高度(像素)，默认 2px")
    parser.add_argument("--glow", type=int, default=12, help="垂直泛光晕染深度(像素)，默认 12px")
    parser.add_argument("--fade-x", type=int, default=45, help="左右两侧渐变收尾半径(像素)，默认 45px")
    parser.add_argument("--color", type=str, default="#00E5FF", help="光芒颜色十六进制，默认 #00E5FF (亮青色)")
    parser.add_argument("--primary-only", action="store_true", help="仅在主显示器显示，不传则在所有扩展屏幕上均显示")
    parser.add_argument("--interval", type=int, default=300, help="心跳同步间隔(毫秒)，默认 300ms")
    parser.add_argument("--daemon", action="store_true", help="静默在后台启动")
    parser.add_argument("--stop", action="store_true", help="停止当前正在运行的指示条进程")
    args = parser.parse_args()

    if args.stop:
        stop_running_instance()
        return

    if args.daemon:
        stop_running_instance()
        pythonw_path = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pythonw_path):
            pythonw_path = "pythonw.exe"

        script_path = os.path.abspath(__file__)
        cmd = [
            pythonw_path,
            script_path,
            "--width-ratio", str(args.width_ratio),
            "--height", str(args.height),
            "--glow", str(args.glow),
            "--fade-x", str(args.fade_x),
            "--color", args.color,
            "--interval", str(args.interval)
        ]
        if args.primary_only:
            cmd.append("--primary-only")

        subprocess.Popen(cmd)
        print("============================================================")
        print("【方案 A：顶端发光条 (Bloom Edition) 已在后台启动】")
        print(f"宽度: {int(args.width_ratio * 100)}% 屏幕居中 | 核心高度: {args.height}px | 泛光高度: {args.glow}px")
        print("如需停止，请双击 stop_indicator.bat 或执行 python top_indicator.py --stop")
        print("============================================================")
        return

    app = IndicatorApp(
        width_ratio=args.width_ratio,
        height=args.height,
        glow=args.glow,
        fade_x=args.fade_x,
        color=parse_color(args.color),
        primary_only=args.primary_only,
        heartbeat_interval=args.interval
    )
    app.run()

if __name__ == "__main__":
    main()
