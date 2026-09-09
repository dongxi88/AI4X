# 键盘连接检测与屏幕顶端发光指示工具

针对两台电脑通过 USB Hub / KVM 切换器共用一套键盘的办公场景，提供**毫秒级键盘连接状态检测**与**优雅防打扰的屏幕顶端发光指示条 (Bloom Edition)**。

---

## 🌟 特性概览

- **余光秒懂，优雅防打扰**：屏幕正上方居中 1/4 宽度、2px 极细微白实体亮线 + 12px 柔和青蓝泛光（Bloom）晕染，完全匹配原型设计。
- **100% 绝对鼠标穿透**：底层采用 `WS_EX_TRANSPARENT` 与 `WM_NCHITTEST (HTTRANSPARENT)`，鼠标在指示条区域点击、拖拽网页标签、软件标题栏完全无阻碍。
- **双通道毫秒级即时响应**：集成 Windows `WM_DEVICECHANGE` 硬件热插拔广播与 300ms 心跳保活，按下 USB Hub 切换按键瞬间自动点亮/熄灭。
- **极度轻量低功耗**：
  - **CPU 占用**：`0.000%`（Win32 消息循环内核休眠等待）
  - **物理内存 (RAM)**：`~23 MB`（专用提交仅 `11 MB`）
  - **显存占用**：`~40 KB`（DWM 硬件加速合成，零持续重绘）
- **多显示器扩展模式自适应**：支持多屏扩展环境，自动根据屏幕分辨率居中计算贴合坐标。

---

## 🚀 快速使用

### 1. 一键后台启动
双击运行项目目录下的 `start.bat`（或 `start_indicator.bat`）：
```bat
start.bat
```
- 无黑框命令行窗口，静默常驻后台运行。
- 若键盘接入本机，屏幕顶部中央即刻泛起柔和青色光晕；切换走后即刻熄灭。

### 2. 一键停止
双击运行 `stop.bat`（或 `stop_indicator.bat`）：
```bat
stop.bat
```
- 安全退出后台指示条进程并释放资源。

### 3. 命令行高级启动与调试
可以通过 Python 传参自定义视觉样式：
```powershell
# 自定义示例：宽度占 30%，高度 3px，泛光 15px，金黄色 (#FFB700)
python top_indicator.py --width-ratio 0.3 --height 3 --glow 15 --color "#FFB700"

# 仅检测键盘连接状态（终端输出文本报告）
python detect_keyboard.py

# 终端实时监听 Hub 切换测试模式
python detect_keyboard.py -w
```

---

## 📂 文件清单与导航

| 文件 | 描述 |
| :--- | :--- |
| [`top_indicator.py`](./top_indicator.py) | **核心指示条程序**：Win32 32位 ARGB 分层窗口 + 硬件加速泛光合成 |
| [`start_indicator.bat`](./start_indicator.bat) | **一键启动脚本**：静默拉起后台指示条 |
| [`stop_indicator.bat`](./stop_indicator.bat) | **一键停止脚本**：安全关闭后台进程 |
| [`detect_keyboard.py`](./detect_keyboard.py) | **连接检测核心库**：基于 Windows RawInput 过滤并识别打字键盘 |
| [`PERFORMANCE.md`](./PERFORMANCE.md) | **系统资源消耗与性能基准测试报告** |
| [`PROTOTYPES.md`](./PROTOTYPES.md) | 三套视觉设计方案与原型分析对比 |
| [`assets/`](./assets/) | 原型设计图与发光效果预览图 |
| [`runtime.log`](./runtime.log) | 硬件插拔与状态同步调试日志 |

---

## ⚙️ 开机自启设置
按下 `Win + R` 输入 `shell:startup` 回车，将 `start_indicator.bat` 的快捷方式粘贴进该目录即可实现开机自动静默驻留。
