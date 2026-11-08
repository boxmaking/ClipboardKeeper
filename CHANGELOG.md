---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 3eb4ecfa3edbbceeda685b8d17a76639_a6b2fa71db8e11f19232525400248c00
    ReservedCode1: Tdc+boSroSl2lU24gCZiVZYlapywxuFCv3pHxrpr5mo71c2ylfkKwXokF2wBlvU8GtKXpuTv8uWhYybS8fVxRpRprnQ8fgnxBjFQpj17rxecVxENomRiSnZvIawS1GFajZg8ksf/4VtsXaCCnsDY0AUffywO5r7ytdGVh6Zf9e/xyCzuZC5k07xoY0Y=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 3eb4ecfa3edbbceeda685b8d17a76639_a6b2fa71db8e11f19232525400248c00
    ReservedCode2: Tdc+boSroSl2lU24gCZiVZYlapywxuFCv3pHxrpr5mo71c2ylfkKwXokF2wBlvU8GtKXpuTv8uWhYybS8fVxRpRprnQ8fgnxBjFQpj17rxecVxENomRiSnZvIawS1GFajZg8ksf/4VtsXaCCnsDY0AUffywO5r7ytdGVh6Zf9e/xyCzuZC5k07xoY0Y=
---

# 更新日志

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)：`主版本.次版本.修订号`。

## v2.1.0 — 2026-11-09

### 新增

- **系统托盘图标**：启动后常驻任务栏通知区域，悬停显示 `ClipboardKeeper · 运行中 · 文本 N / 图片 M`，双击打开当月记录文件。
- **右键菜单**：状态统计（只读）、打开当月记录文件、打开归档目录、打开配置文件、查看运行日志、暂停/继续监听、退出。
- **暂停/恢复监听**：暂停期间停止抓取但保留进程与图标，恢复后从当前剪贴板重新开始；暂停时丢弃期间的剪贴板变化，不补记。
- **托盘开关**：新增配置项 `tray_enabled`（默认 `true`）与命令行参数 `--no-tray`，可回到无图标的纯静默模式。
- **自动生成图标**：首次运行用 Pillow 绘制 16/24/32/48/256 多尺寸 `logs/tray.ico`；缺 Pillow 或绘制失败时回退系统默认图标，托盘功能不受影响。

### 变更

- 托盘基于 `Shell_NotifyIconW` + 隐藏窗口 + 独立消息线程实现，仍保持零第三方依赖，单文件可运行。
- 图标挂载失败只在日志中记录并降级为无图标运行，不影响剪贴板记录主流程。

### 已知问题

- 托盘图标位于通知区域溢出区时需点 `^` 展开才能看到，这是 Windows 的默认收纳行为。

## v2.0.0 — 2026-11-08

首个公开发布版本。

### 新增

- **序号轮询**：改用 `GetClipboardSequenceNumber()` 检测剪贴板变化，内容不变时完全不读取剪贴板，CPU 占用与剪贴板锁竞争显著下降。
- **配置热加载**：修改 `config.json` 后约 2 秒内自动生效，无需重启进程。
- **图片格式可选**：`image_format` 支持 `png`（无损）与 `jpg`（体积小，质量可调）；`image_max_side` 可限制最长边，避免超大截图占满磁盘。
- **命令行接口**：`--console` / `--once` / `--status` / `--init-config` / `--version`。
- **带注释的配置文件**：自动生成的 `config.json` 支持 `//` 注释，每个键都带中文说明。
- **运行状态查询**：`--status` 显示进程状态、当前归档文件、条目数与图片目录占用。
- **日志分级与轮转**：`INFO` / `WARN` / `ERROR` 三级，超过阈值自动轮转。
- **PID 文件**：`run.pid` 记录当前进程号，`stop.bat` 可精确停止。
- **优雅退出**：捕获 `Ctrl+C`、`SIGTERM`、`SIGBREAK`，退出前写入统计日志。
- **配置自适应**：非法或缺失的配置项自动回退默认值，兼容旧版配置文件。

### 变更

- 记录格式统一为纯文本（UTF-8 无 BOM），按月分文件，取消早期的 JSONL / Markdown 双写。
- 图片附件统一存放在 `<output_dir>/images/`，正文中记录相对路径。
- 单实例保护改用命名互斥量 `Local\ClipboardKeeper_SingleInstance`。
- 启动脚本不再硬编码 Python 路径，改为从 `PATH` 查找。

### 修复

- 剪贴板被占用（`OpenClipboard` 失败）时不再丢弃该次内容，下一轮自动重试。
- 程序重启后不会重复记录最后一条内容（去重状态持久化在 `logs/last_hash.txt`）。
- 大文本截断时补充原文字符数提示。

## v1.0.0 — 2026-11-05

- 初始版本：WinAPI 剪贴板监听，文本与图片双捕获，按天输出 Markdown 与 JSONL。
*（内容由AI生成，仅供参考）*
