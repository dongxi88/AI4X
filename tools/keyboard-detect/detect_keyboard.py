"""
键盘连接检测与 Hub 切换监听工具
通过 Windows RawInput API 实时检测当前电脑是否连接了键盘。
针对 USB Hub / KVM 切换器场景提供单次检测、实时监控以及目标键盘绑定功能。

特性：
- 自动枚举系统鼠标设备，动态识别并过滤蓝牙/无线鼠标接收器、游戏鼠标侧键宏等“伪键盘”端点
- 支持任意品牌外接打字键盘通用即插即用检测
- 支持定向绑定（--bind），锁定仅监听特定 USB Hub 共享键盘，彻底杜绝其他外设干扰
"""

import sys
import os
import time
import argparse
import ctypes
from ctypes import wintypes
import re
import json

# 解决 Windows 控制台默认编码兼容性
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")

class RAWINPUTDEVICELIST(ctypes.Structure):
    _fields_ = [
        ('hDevice', wintypes.HANDLE),
        ('dwType', wintypes.DWORD)  # 1: RIM_TYPEKEYBOARD, 0: RIM_TYPEMOUSE, 2: RIM_TYPEHID
    ]

RIM_TYPEMOUSE = 0
RIM_TYPEKEYBOARD = 1
RIDI_DEVICENAME = 0x20000007

# 常用已知键盘友好名称库（用于输出展示优化，未收录设备依然正常检测）
KNOWN_KEYBOARDS = {
    ("258A", "002A"): ("黑峡谷 (Hexgears) 机械键盘", False),
    ("258A", "1007"): ("黑峡谷游戏鼠标 (侧键宏映射端点)", True),
    ("046D", "C341"): ("罗技 (Logitech) 机械键盘", False),
    ("046D", "C52B"): ("罗技 (Logitech) Unifying 无线接收器", True),
    ("046D", "C534"): ("罗技 (Logitech) 无线键鼠接收器", True),
    ("1532", "0084"): ("雷蛇 (Razer) 电竞鼠标", True),
}

def load_config():
    """读取目标键盘绑定配置"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_config(cfg):
    """保存目标键盘绑定配置"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def get_raw_devices():
    """使用 Windows 原生 RawInput API 获取所有当前接入的键盘与鼠标设备硬件路径"""
    user32 = ctypes.windll.user32
    num_devices = wintypes.UINT(0)
    
    if user32.GetRawInputDeviceList(None, ctypes.byref(num_devices), ctypes.sizeof(RAWINPUTDEVICELIST)) != 0:
        return [], []
    
    if num_devices.value == 0:
        return [], []

    devices = (RAWINPUTDEVICELIST * num_devices.value)()
    ret = user32.GetRawInputDeviceList(devices, ctypes.byref(num_devices), ctypes.sizeof(RAWINPUTDEVICELIST))
    if ret == -1:
        return [], []

    keyboards = []
    mice = []
    for dev in devices:
        name_len = wintypes.UINT(0)
        user32.GetRawInputDeviceInfoW(dev.hDevice, RIDI_DEVICENAME, None, ctypes.byref(name_len))
        if name_len.value > 0:
            buf = ctypes.create_unicode_buffer(name_len.value)
            user32.GetRawInputDeviceInfoW(dev.hDevice, RIDI_DEVICENAME, buf, ctypes.byref(name_len))
            if dev.dwType == RIM_TYPEKEYBOARD:
                keyboards.append(buf.value)
            elif dev.dwType == RIM_TYPEMOUSE:
                mice.append(buf.value)
    return keyboards, mice

def parse_device_info(raw_name, mouse_vid_pids=None):
    """解析 RawInput 设备路径中的 VID / PID，并动态识别鼠标复合扩展端点"""
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

        # 1. 显式已知库匹配
        if (vid, pid) in KNOWN_KEYBOARDS:
            desc, is_mouse = KNOWN_KEYBOARDS[(vid, pid)]
            info["description"] = desc
            info["is_mouse_macro"] = is_mouse
        # 2. 动态自动识别：如果该 VID/PID 同时作为系统鼠标设备存在，自动识别为鼠标复合端点
        elif mouse_vid_pids and (vid, pid) in mouse_vid_pids:
            info["description"] = f"鼠标/无线接收器扩展按键端点 (VID:{vid} PID:{pid})"
            info["is_mouse_macro"] = True
        else:
            info["description"] = f"USB 键盘 (VID:{vid} PID:{pid})"

    return info

def check_status(target=None):
    """
    检测当前状态
    1. 动态比对鼠标端点，自动排除无线鼠标接收器与侧键宏
    2. 支持读取 config.json 或参数传入的定向绑定键盘
    """
    raw_keyboards, raw_mice = get_raw_devices()
    
    # 动态搜集系统内所有鼠标设备的 (VID, PID)
    mouse_vid_pids = set()
    for m_raw in raw_mice:
        m = re.search(r'VID_([0-9A-F]{4})&PID_([0-9A-F]{4})', m_raw.upper())
        if m:
            mouse_vid_pids.add((m.group(1), m.group(2)))

    parsed = [parse_device_info(d, mouse_vid_pids) for d in raw_keyboards]
    
    # 检查是否有定向绑定配置
    cfg = load_config()
    target_vid = (target or cfg.get("target_vid", "")).upper()
    target_pid = (cfg.get("target_pid", "")).upper()
    
    if target_vid:
        if target_pid:
            physical_keyboards = [d for d in parsed if d["vid"] == target_vid and d["pid"] == target_pid]
        else:
            physical_keyboards = [d for d in parsed if d["vid"] == target_vid and not d["is_mouse_macro"]]
    else:
        # 自动排除所有鼠标扩展端点
        physical_keyboards = [d for d in parsed if not d["is_mouse_macro"]]
    
    unique_names = list(dict.fromkeys(d["description"] for d in physical_keyboards))
    
    return {
        "connected": len(physical_keyboards) > 0,
        "keyboard_names": unique_names,
        "physical_keyboards": physical_keyboards,
        "all_keyboard_endpoints": parsed,
        "is_target_mode": bool(target_vid),
        "target_info": f"VID:{target_vid} PID:{target_pid}" if target_vid else None
    }

def print_status_report():
    status = check_status()
    print("=" * 65)
    print("【键盘连接检测报告】")
    print(f"检测时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    if status["is_target_mode"]:
        print(f"监听模式: 【定向绑定模式】(锁定目标: {status['target_info']})")
    else:
        print("监听模式: 【智能通用模式】(自动识别实体键盘并剔除鼠标接收器)")
    print("-" * 65)
    
    if status["connected"]:
        print("状态: [已连接] (CONNECTED)")
        print(f">> 当前接入本机的实体键盘: {', '.join(status['keyboard_names'])}")
    else:
        print("状态: [未连接] (DISCONNECTED)")
        print(">> 当前本机未检测到实体打字键盘。")
        print("   原因: 键盘当前已被 USB Hub 切换到了【另外一台电脑】。")

    print("\n[当前系统枚举的键盘类端点及过滤状态]:")
    if not status["all_keyboard_endpoints"]:
        print("  (未发现任何键盘端点)")
    else:
        for idx, dev in enumerate(status["all_keyboard_endpoints"], 1):
            if dev["is_mouse_macro"]:
                tag = "[鼠标扩展端点 - 已自动过滤]"
            else:
                tag = "[实体打字键盘 - 识别生效]"
            print(f"  {idx}. {tag} {dev['description']}")
            print(f"     设备标识: {dev['raw']}")
            
    print("=" * 65)

def bind_target_keyboard():
    """一键将当前连接的打字键盘绑定为目标设备"""
    status = check_status()
    candidates = status["physical_keyboards"]
    if not candidates:
        print("[错误] 当前未检测到已连接的实体打字键盘，请先插上键盘或切换到本机后再运行此命令。")
        return

    # 去重
    unique_candidates = []
    seen = set()
    for c in candidates:
        pair = (c["vid"], c["pid"])
        if pair not in seen and c["vid"] and c["pid"]:
            seen.add(pair)
            unique_candidates.append(c)

    if len(unique_candidates) == 1:
        chosen = unique_candidates[0]
    else:
        print("检测到多把实体打字键盘，请选择要绑定的目标键盘：")
        for i, c in enumerate(unique_candidates, 1):
            print(f"  [{i}] {c['description']} (VID:{c['vid']} PID:{c['pid']})")
        try:
            choice = int(input("请输入序号 [1]: ").strip() or "1")
            chosen = unique_candidates[choice - 1]
        except Exception:
            chosen = unique_candidates[0]

    cfg = {
        "target_vid": chosen["vid"],
        "target_pid": chosen["pid"],
        "target_name": chosen["description"],
        "bound_at": time.strftime('%Y-%m-%d %H:%M:%S')
    }
    if save_config(cfg):
        print("=" * 65)
        print("【成功】已将该键盘设为目标绑定设备！")
        print(f"设备名称: {chosen['description']}")
        print(f"硬件标识: VID:{chosen['vid']} PID:{chosen['pid']}")
        print("从此指示条将 100% 专一追踪此键盘，任何蓝牙鼠标接收器都不会造成误触发。")
        print(f"配置文件已生成在: {CONFIG_FILE}")
        print("如需恢复通用检测，执行: python detect_keyboard.py --unbind")
        print("=" * 65)
    else:
        print("[错误] 保存配置文件失败。")

def unbind_target_keyboard():
    """解绑并恢复智能通用检测模式"""
    if os.path.exists(CONFIG_FILE):
        try:
            os.remove(CONFIG_FILE)
            print("[成功] 已移除目标绑定配置，恢复为【智能通用检测模式】。")
        except Exception as e:
            print(f"[错误] 删除配置文件失败: {e}")
    else:
        print("[提示] 当前未设置绑定目标，已处于智能通用模式。")

def watch_mode(interval=0.5):
    print("=" * 65)
    print(f"【实时监听模式已启动】(检测间隔: {interval}s)")
    print("现在您可以按 USB Hub / KVM 上的切换按钮，状态发生改变时会在此实时打印。")
    print("按 Ctrl+C 即可退出监控。")
    print("=" * 65)
    
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
    parser.add_argument("--bind", action="store_true", help="将当前连接的键盘保存为目标绑定设备")
    parser.add_argument("--unbind", action="store_true", help="解除绑定，恢复为智能通用检测模式")
    args = parser.parse_args()

    if args.bind:
        bind_target_keyboard()
    elif args.unbind:
        unbind_target_keyboard()
    elif args.watch:
        watch_mode(args.interval)
    else:
        print_status_report()
