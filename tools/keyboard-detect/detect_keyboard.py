"""
键盘连接检测与 Hub 切换监听工具
通过 Windows RawInput API 实时检测当前电脑是否连接了键盘。
针对 USB Hub / KVM 切换器场景提供单次检测与实时监控模式。
"""

import sys
import time
import argparse
import ctypes
from ctypes import wintypes
import re

# 解决 Windows 控制台默认编码兼容性
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

class RAWINPUTDEVICELIST(ctypes.Structure):
    _fields_ = [
        ('hDevice', wintypes.HANDLE),
        ('dwType', wintypes.DWORD)  # 1: RIM_TYPEKEYBOARD, 0: RIM_TYPEMOUSE, 2: RIM_TYPEHID
    ]

RIM_TYPEKEYBOARD = 1
RIDI_DEVICENAME = 0x20000007

KNOWN_KEYBOARDS = {
    ("258A", "002A"): ("黑峡谷 (Hexgears) 机械键盘", False),
    ("258A", "1007"): ("黑峡谷游戏鼠标 (Hexgears Gaming Mouse 侧键宏映射端点)", True),
    ("046D", "C341"): ("罗技 (Logitech) 机械键盘", False),
}

def get_raw_keyboards():
    """使用 Windows 原生 RawInput API 获取所有当前接入的键盘设备硬件路径"""
    user32 = ctypes.windll.user32
    num_devices = wintypes.UINT(0)
    
    if user32.GetRawInputDeviceList(None, ctypes.byref(num_devices), ctypes.sizeof(RAWINPUTDEVICELIST)) != 0:
        return []
    
    if num_devices.value == 0:
        return []

    devices = (RAWINPUTDEVICELIST * num_devices.value)()
    ret = user32.GetRawInputDeviceList(devices, ctypes.byref(num_devices), ctypes.sizeof(RAWINPUTDEVICELIST))
    if ret == -1:
        return []

    keyboards = []
    for dev in devices:
        if dev.dwType == RIM_TYPEKEYBOARD:
            name_len = wintypes.UINT(0)
            user32.GetRawInputDeviceInfoW(dev.hDevice, RIDI_DEVICENAME, None, ctypes.byref(name_len))
            if name_len.value > 0:
                buf = ctypes.create_unicode_buffer(name_len.value)
                user32.GetRawInputDeviceInfoW(dev.hDevice, RIDI_DEVICENAME, buf, ctypes.byref(name_len))
                keyboards.append(buf.value)
    return keyboards

def parse_device_info(raw_name):
    """解析 RawInput 设备路径中的 VID / PID 等标识"""
    upper_name = raw_name.upper()
    info = {
        "raw": raw_name,
        "vid": None,
        "pid": None,
        "is_mouse_macro": False,
        "description": "未知 USB 键盘设备"
    }

    m = re.search(r'VID_([0-9A-F]{4})&PID_([0-9A-F]{4})', upper_name)
    if m:
        vid, pid = m.group(1), m.group(2)
        info["vid"] = vid
        info["pid"] = pid
        if (vid, pid) in KNOWN_KEYBOARDS:
            desc, is_mouse = KNOWN_KEYBOARDS[(vid, pid)]
            info["description"] = desc
            info["is_mouse_macro"] = is_mouse
        else:
            info["description"] = f"USB 键盘 (VID:{vid} PID:{pid})"

    return info

def check_status():
    """检测当前状态"""
    devices = get_raw_keyboards()
    parsed = [parse_device_info(d) for d in devices]
    
    # 实体物理打字键盘（排除鼠标宏按键端点）
    physical_keyboards = [d for d in parsed if not d["is_mouse_macro"]]
    
    # 汇总主要的键盘名称
    unique_names = list(dict.fromkeys(d["description"] for d in physical_keyboards))
    
    return {
        "connected": len(physical_keyboards) > 0,
        "keyboard_names": unique_names,
        "physical_keyboards": physical_keyboards,
        "all_keyboard_endpoints": parsed
    }

def print_status_report():
    status = check_status()
    print("=" * 60)
    print("【键盘连接检测报告】")
    print(f"检测时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    if status["connected"]:
        print("状态: [已连接] (CONNECTED)")
        print(f">> 当前接入本机的实体键盘: {', '.join(status['keyboard_names'])}")
    else:
        print("状态: [未连接] (DISCONNECTED)")
        print(">> 当前本机未检测到实体打字键盘。")
        print("   原因: 键盘当前已被 USB Hub 切换到了【另外一台电脑】。")

    print("\n[当前电脑上的键盘类设备端点列表]:")
    if not status["all_keyboard_endpoints"]:
        print("  (无任何键盘端点)")
    else:
        for idx, dev in enumerate(status["all_keyboard_endpoints"], 1):
            tag = "[鼠标宏按键端点]" if dev["is_mouse_macro"] else "[实体打字键盘]"
            print(f"  {idx}. {tag} {dev['description']}")
            print(f"     设备标识: {dev['raw']}")
            
    print("=" * 60)

def watch_mode(interval=0.5):
    print("=" * 60)
    print(f"【实时监听模式已启动】(检测间隔: {interval}s)")
    print("现在您可以按 USB Hub / KVM 上的切换按钮，状态发生改变时会在此实时打印。")
    print("按 Ctrl+C 即可退出监控。")
    print("=" * 60)
    
    last_connected = None
    last_keyboards_str = ""
    try:
        while True:
            status = check_status()
            curr_connected = status["connected"]
            curr_str = ", ".join(status["keyboard_names"])
            
            now = time.strftime('%H:%M:%S')
            if last_connected is None:
                last_connected = curr_connected
                last_keyboards_str = curr_str
                if curr_connected:
                    print(f"[{now}] 初始状态: 键盘【已连接到本机】({curr_str}) [OK]")
                else:
                    print(f"[{now}] 初始状态: 键盘【未连接 / 在另一台电脑】[DISCONNECTED]")
            elif curr_connected != last_connected or (curr_connected and curr_str != last_keyboards_str):
                if curr_connected:
                    print(f"\n>> [{now}] 提示: 键盘已切换接入【本机】！({curr_str}) [CONNECTED]")
                else:
                    print(f"\n>> [{now}] 提示: 键盘已断开（已切换到【另一台电脑】）！[DISCONNECTED]")
                last_connected = curr_connected
                last_keyboards_str = curr_str
                
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n监听已停止。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="检测键盘连接状态与 Hub 切换监听")
    parser.add_argument("-w", "--watch", action="store_true", help="进入持续监控模式，实时查看 Hub 切换")
    parser.add_argument("-i", "--interval", type=float, default=0.5, help="监控轮询间隔(秒)，默认 0.5s")
    args = parser.parse_args()

    if args.watch:
        watch_mode(args.interval)
    else:
        print_status_report()
