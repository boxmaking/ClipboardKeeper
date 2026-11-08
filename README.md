---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 3eb4ecfa3edbbceeda685b8d17a76639_7e20baafdb8f11f19280525400393706
    ReservedCode1: RwxhSuO2P0KvRKYi4h0lmjAiZvjn8QJkPyWK+1sSDrCA75qPqGR2Prv8IGnl9qyLvVVCRtX1PZp4T3q8baDsPtn30o+TRqanJlTh5UHODvY3Aygic8GN6u5jsPLTzFUsolYSJgOG7k/ib7JTz910yXfFtNjHds12P4EhGnGH/85t6D1Qc701yXK5N0s=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 3eb4ecfa3edbbceeda685b8d17a76639_7e20baafdb8f11f19280525400393706
    ReservedCode2: RwxhSuO2P0KvRKYi4h0lmjAiZvjn8QJkPyWK+1sSDrCA75qPqGR2Prv8IGnl9qyLvVVCRtX1PZp4T3q8baDsPtn30o+TRqanJlTh5UHODvY3Aygic8GN6u5jsPLTzFUsolYSJgOG7k/ib7JTz910yXfFtNjHds12P4EhGnGH/85t6D1Qc701yXK5N0s=
---



# ClipboardKeeper

**Windows 下把剪贴板变成可搜索的笔记。** 一个常驻后台、无界面、零配置的小工具：你复制过的文字和截图，自动带上毫秒时间戳，写进按月分割的纯文本文件。

![License](https://img.shields.io/badge/license-GPL--2.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8%2B-3776AB.svg?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Windows-0078D6.svg?logo=windows&logoColor=white)
![Dependencies](https://img.shields.io/badge/dependencies-none-success.svg)

---

## 目录

- [它解决什么问题](#它解决什么问题)
- [特性](#特性)
- [快速开始](#快速开始)
- [日常使用](#日常使用)
- [托盘图标](#托盘图标)
- [归档长什么样](#归档长什么样)
- [配置](#配置)
- [命令行](#命令行)
- [开机自启](#开机自启)
- [工作原理](#工作原理)
- [常见问题](#常见问题)
- [隐私与安全](#隐私与安全)
- [已知限制](#已知限制)
- [目录结构](#目录结构)
- [参与贡献](#参与贡献)
- [许可证](#许可证)

---

## 它解决什么问题

Win + V 的剪贴板历史有两个限制：**只留 25 条**，**重启就清空**。

于是有些事做不成：找回上午复制的一段报错、翻出昨天截的一张图、确认上周从文档里抠出来的那行数据到底是 `0.35` 还是 `0.53`。

ClipboardKeeper 的做法很简单——不抢剪贴板、不做 UI、不做数据库，只把每次复制**追加成一行纯文本**。想找内容，用编辑器搜索，或者：

```bat
findstr /s /i "骨料级配" C:\Users\你\ClipboardKeeper\*.txt
```

## 特性

**核心能力**

- **纯文本归档** — UTF-8（无 BOM），按 `月` 或 `日` 分文件，任何编辑器可读，可被全文搜索工具索引。
- **文本 + 图片双捕获** — 复制文字记文字，截图记图片并落盘为 `png` / `jpg`。
- **毫秒时间戳** — 每条记录形如 `[2026-11-09 00:10:07.868]`，能精确对上当时的操作。
- **自动去重** — SHA-1 内容指纹比对；同一内容复制多次只记一条，且状态跨重启保持。
- **忽略规则** — 用正则排除不想落盘的内容（密码、验证码、私钥片段）。

**工程性**

- **近乎零开销** — 基于 `GetClipboardSequenceNumber()`，剪贴板没变化时**完全不读取**；常态 CPU 占用接近 0，内存 15–25 MB。
- **零第三方依赖** — 只用标准库 + Win32 API。Pillow 仅在保存图片时需要，且为可选。
- **配置热加载** — 改完 `config.json` 约 2 秒生效，不必重启进程。
- **单实例保护** — 命名互斥量兜底，重复启动会立即退出，不会双写同一文件。
- **静默运行** — 通过 `pythonw.exe` 启动，无窗口、无弹窗；仅在任务栏通知区域留一个托盘图标，用于查看状态与快捷操作。
- **状态自检** — `--status` 一次看清进程、归档文件、条目数、图片占用。
- **可逆部署** — 开机自启用启动目录而非注册表，卸载无残留。

## 快速开始

**要求**：Windows 7 SP1 / 10 / 11，Python 3.8+（安装时勾选 *Add Python to PATH*）。

```bat
:: 1. 进入程序目录
cd ClipboardKeeper

:: 2. 后台启动
start.bat
```

就这两步。首次启动会自动生成带注释的 `config.json` 与归档目录，随后随便复制点东西验证：

```bat
python clipboard_keeper.py --status
```

**可选**：安装 Pillow 以保存图片（不装则只记文本，程序照常工作）。

```bat
pip install pillow
```

## 日常使用

| 场景 | 做法 |
| --- | --- |
| 后台启动（无窗口） | 双击 `start.bat` |
| 停止 | 双击 `stop.bat`，或右键托盘图标 → 退出 |
| 打开当月记录 | 双击托盘图标，或右键 → 打开当月记录文件 |
| 临时暂停/恢复抓取 | 右键托盘图标 → 暂停监听 / 继续监听 |
| 边跑边看实时输出（调试） | 双击 `run_console.bat` |
| 查看运行状态 | `python clipboard_keeper.py --status` |
| 只抓一次当前剪贴板（排查） | `python clipboard_keeper.py --once` |
| 开机自启 | 双击 `install_autostart.bat` |
| 取消开机自启 | 双击 `uninstall_autostart.bat` |

启动之后正常工作即可，它会安静地待在后台。想验证捕获是否生效，复制一句话，再打开当月的 `.txt` 看最后一段。

## 托盘图标

启动后任务栏通知区域会出现一个蓝底剪贴板图标（在托盘溢出区里，点 `^` 展开可见）。

| 操作 | 效果 |
| --- | --- |
| 悬停 | 提示当前状态：`ClipboardKeeper · 运行中 · 文本 12 / 图片 3` |
| 双击 | 打开当月记录文件 |
| 右键 | 弹出菜单：状态统计、打开当月记录文件、打开归档目录、打开配置文件、查看运行日志、暂停/继续监听、退出 |

- 菜单首行「本次已记录 文本 N / 图片 M」是本进程启动以来的计数，只读展示。
- 「暂停监听」只停抓取，进程与图标保留，恢复后从当前剪贴板重新开始（暂停期间复制的内容不补记）。
- 不想看图标就把 `config.json` 里的 `tray_enabled` 改成 `false`，或启动时加 `--no-tray`。
- 图标文件首次运行时生成到 `logs/tray.ico`；生成失败（如缺 Pillow）会回退系统默认图标，托盘功能不受影响，删掉该文件会自动重建。

## 归档长什么样

`2026-11.txt` 直接双击就能读：

```
剪贴板记录  2026-11
========================================================================

[2026-11-09 00:10:07.868] 文本 · 54 字符
------------------------------------------------------------------------
SELECT * FROM orders WHERE created_at > '2026-11-01';

[2026-11-09 00:10:10.626] 图片 · 320×160
------------------------------------------------------------------------
图片文件: images\2026-11-09_001010_626.png

[2026-11-09 00:12:44.310] 文本 · 12 字符
------------------------------------------------------------------------
待办：核对骨料级配
```

规则说明：

- 每条格式为 `[时间戳] 类型 · 摘要`，下接一整行 `-` 分隔，再下是正文。
- 文本超过 `max_text_length` 会被截断，并在末尾注明原始字符数。
- 图片来源显示像素尺寸，实体文件在 `images\` 下，文件名即时间戳，正文只留相对路径。
- 纯空白内容不记录。

## 配置

配置文件 `config.json` 位于程序同目录，**支持 `//` 注释**（首次运行自动生成，或执行 `--init-config`）。

```jsonc
{
  "output_dir": "history",          // 归档根目录，相对路径基于程序所在目录
  "group_by": "month",              // month=按月 / day=按天
  "poll_interval": 0.8,             // 轮询间隔（秒），最小 0.2
  "capture_text": true,             // 是否记录文本
  "capture_images": true,           // 是否记录图片
  "image_format": "png",            // png=无损 / jpg=体积小
  "image_quality": 92,              // jpg 质量，1-100
  "image_max_side": 0,              // 图片最长边上限（像素），0=不缩放
  "max_text_length": 200000,        // 单条文本最大字符数，超出截断
  "ignore_patterns": [],            // 正则数组，命中则跳过该条
  "log_enabled": true,              // 是否写运行日志
  "log_max_bytes": 2097152,         // 日志轮转阈值（字节）
  "tray_enabled": true,             // 是否显示托盘图标
  "console_echo": false             // 是否回显到控制台
}
```

| 键 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `output_dir` | string | `"history"` | 归档根目录。支持环境变量与 `~`；相对路径相对程序目录 |
| `group_by` | string | `"month"` | `month` 单文件更整齐；`day` 便于按天切分与清理 |
| `poll_interval` | number | `0.8` | 调小更灵敏、更耗 CPU；调大更省电 |
| `capture_text` | bool | `true` | 关掉则只记图片 |
| `capture_images` | bool | `true` | 关掉则只记文本 |
| `image_format` | string | `"png"` | `jpg` 体积约为 png 的 1/5～1/10 |
| `image_quality` | int | `92` | 仅 `jpg` 生效 |
| `image_max_side` | int | `0` | 如 `1920`，超过的截图等比缩小 |
| `max_text_length` | int | `200000` | 防止误复制超大文本撑爆文件 |
| `ignore_patterns` | array | `[]` | 正则数组，**任一命中即跳过** |
| `log_enabled` | bool | `true` | 关闭后不写日志 |
| `log_max_bytes` | int | `2097152` | 超过即轮转为 `.log.1` |
| `tray_enabled` | bool | `true` | 关闭后不显示托盘图标，回到纯静默 |
| `console_echo` | bool | `false` | 前台调试时有用，后台运行时无意义 |

配置非法或缺失时自动回退默认值，不会因为写错一个键就启动失败。

### 场景示例

**归档放到独立目录，截图压缩后再存**

```jsonc
{
  "output_dir": "D:\\Clipboard",
  "image_format": "jpg",
  "image_quality": 88,
  "image_max_side": 1920
}
```

**排除敏感内容**

```jsonc
{
  "ignore_patterns": ["^password", "passwd", "\\b\\d{6}\\b", "^-----BEGIN"]
}
```

**按天归档，便于定期清理**

```jsonc
{
  "group_by": "day"
}
```

> `ignore_patterns` 是**写入前拦截**，不是安全隔离——内容仍会被读取一次再判断。别把它当密码管理器用。

## 命令行

```
用法: python clipboard_keeper.py [选项]

  -c, --console     前台运行，并把每条记录回显到控制台
      --once        只抓取一次当前剪贴板后退出
      --no-tray     本次启动不显示托盘图标
      --status      打印运行状态与统计后退出
      --init-config 生成带注释的默认 config.json 后退出
  -v, --version     显示版本与许可证标识
  -h, --help        显示帮助
```

`--status` 输出示例：

```
ClipboardKeeper 2.0.0  (GPL-2.0-or-later)
运行状态 : 运行中, PID 22640
输出目录 : C:\Users\pengshao\ClipboardKeeper
当前文件 : C:\Users\pengshao\ClipboardKeeper\2026-11.txt  (473 B, 约 2 条)
图片目录 : C:\Users\pengshao\ClipboardKeeper\images  (1 个文件, 562 B)
配置文件 : ...\ClipboardKeeper\config.json
日志文件 : ...\ClipboardKeeper\logs\clipboard_keeper.log

关键配置 : 粒度=month  轮询=0.80s  文本=True  图片=True(png)  最大字符=200000
```

## 开机自启

```bat
install_autostart.bat
```

在 `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup` 下创建一个 `ClipboardKeeper.bat`，登录时以 `pythonw` 无窗口拉起。取消用 `uninstall_autostart.bat`。

选择启动目录而非注册表 `Run` 键，好处是卸载时不留痕迹、不会被安全软件误判，缺点是启动目录里多了一个可见文件——权衡后选了前者。

## 工作原理

一条循环，只做四件事：

```
每 0.8 秒 ──┐
            ├─ ① 取 GetClipboardSequenceNumber()
            │     与上次相同 → 直接睡，什么都不读
            ├─ ② 有变化 → 先看 CF_DIB（位图）
            │     命中 → 读 DIB，拼 BMP 文件头，Pillow 解码，存 images\
            ├─ ③ 无位图 → 再看 CF_UNICODETEXT
            │     命中 → 读宽字符文本，正则过滤，必要时截断
            └─ ④ SHA-1 指纹与上次比对，不同才写盘并更新 logs\last_hash.txt
```

几个实现上的取舍：

| 关注点 | 做法 | 为什么这么做 |
| --- | --- | --- |
| CPU 与锁竞争 | 序号轮询，未变化即跳过 | 避免每轮 `OpenClipboard` 抢剪贴板锁、避免高频读大段文本 |
| 剪贴板被占用 | `OpenClipboard` 失败时**不记账**，下轮重试 | 别的程序正在写剪贴板时不能把这次内容丢掉 |
| 图片解码 | `CF_DIB` 缺 BMP 文件头，按 `biSize` / `biBitCount` / `biClrUsed` 算出像素偏移，手拼 `BITMAPFILEHEADER` 再交 Pillow | 不引入 `pywin32` 这类重依赖，保持零依赖 |
| 重复记录 | SHA-1 指纹持久化到 `logs/last_hash.txt` | 重启后不会把最后一条内容再记一遍 |
| 双开 | 命名互斥量，`ERROR_ALREADY_EXISTS` 即退出 | 两个实例会同时写同一文件，产生交错重复行 |
| 编码 | 固定 UTF-8 无 BOM，`\n` 换行 | 跨 Windows / WSL / 各类编辑器一致，方便 `grep` |
| 配置注释 | 自实现注释剥离后再 `json.loads` | 配置可读，又保持标准 JSON 格式 |
| 热加载 | 每 2 秒比对 `config.json` 的 mtime | 改配置不必重启，也不额外起监听线程 |
| 退出 | 捕获 `Ctrl+C` / `SIGTERM` / `SIGBREAK` | 退出前落统计日志、清理 `run.pid` |

## 常见问题

**会把密码记下来吗？**
会。这是它的固有风险——定位是"把剪贴板当笔记"，不是密码库。建议配 `ignore_patterns`，或把归档放在加密卷中。

**只记文字，图片一直不出现？**
大概率没装 Pillow。`pip install pillow` 后重启程序；`--status` 里的"图片目录"会显示 0 个文件。

**在资源管理器里复制文件为什么不记？**
当前只处理 `CF_UNICODETEXT` 与 `CF_DIB`，不解析 `CF_HDROP`（文件列表）。有意留白，避免把整个目录清单写进日志。

**某个软件复制的文字没捕获到？**
部分程序把内容放在私有剪贴板格式里。可先 `run_console.bat` 配合 `--once` 复现验证；只有标准文本格式才会被记录。

**开了两个实例会怎样？**
第二个因互斥量已存在而立即退出，不会重复写入。

**归档放在 iCloud / OneDrive 同步目录里有问题吗？**
文件本身没问题，但同步客户端可能在写入瞬间锁定文件，造成偶发失败（程序记 `ERROR` 日志后继续，不会崩溃）；另外截图体积增长快，注意配额。

**占多少资源？**
内存约 15–25 MB（主要是 Python 解释器本身），无 Pillow 时更低；CPU 常态接近 0%。

**日志里出现"轮询异常"怎么办？**
说明某轮读取抛了异常，程序已自动继续。把 `logs\clipboard_keeper.log` 中的堆栈贴到 Issue 即可。

**卸载干净吗？**
`stop.bat` → 删掉程序目录与归档目录即可。若装过自启，先跑 `uninstall_autostart.bat`。没有注册表写入、没有服务、没有后台计划任务。

## 隐私与安全

- 剪贴板内容以**明文**写入本地磁盘，请自行确认归档目录的访问权限与是否被云盘共享。
- 程序**不联网、不上报、无遥测**，不产生除命令行输出以外的任何外部通信。
- `config.json`、`history/`、`logs/`、`run.pid` 已在 `.gitignore` 中排除，不会被提交到版本库。
- 建议不要把归档目录放在团队共享或公共同步空间中。

## 已知限制

- 仅 Windows（核心依赖 `user32.dll` 剪贴板 API）。
- 不记录文件复制/拖放（`CF_HDROP`）。
- 不记录富文本格式（HTML / RTF），只取纯文本。
- 轮询间隔决定捕获粒度：短于 `poll_interval` 的连续两次复制，可能只留下最后一次。
- 托盘图标是唯一图形元素，没有主窗口与设置界面，所有配置仍改 `config.json`。
- 图片保存依赖 Pillow，未安装时该能力自动降级。

## 目录结构

```
ClipboardKeeper/
├── clipboard_keeper.py        # 主程序，单文件，约 1180 行
├── config.example.json        # 配置样例（克隆后可复制为 config.json）
├── config.json                # 本机实际配置（.gitignore 忽略）
├── start.bat                  # 后台启动
├── stop.bat                   # 停止
├── run_console.bat            # 前台运行 + 实时回显（调试）
├── install_autostart.bat      # 注册开机自启
├── uninstall_autostart.bat    # 取消开机自启
├── README.md
├── CHANGELOG.md
├── LICENSE                    # GNU GPL v2.0 全文
│
├── history/                   # 归档目录（运行时生成）
│   ├── 2026-11.txt            # 当月记录
│   └── images/                # 图片附件，文件名即时间戳
│       └── 2026-11-09_001010_626.png
│
├── logs/                      # 运行日志（运行时生成）
│   ├── clipboard_keeper.log
│   ├── last_hash.txt          # 去重状态
│   └── tray.ico               # 托盘图标（首次运行生成，可删）
└── run.pid                    # 当前进程号（运行时生成）
```

## 参与贡献

Issue 与 PR 都欢迎。提 PR 前请确认：

1. `python -m py_compile clipboard_keeper.py` 通过；
2. 不引入新的第三方依赖（Pillow 除外，且必须可选）；
3. 保持单文件可运行、可通过 `--status` 自检；
4. 若改动记录格式，同步更新本文"归档长什么样"一节与 `CHANGELOG.md`。

## 许可证

**GNU General Public License v2.0 or later（GPL-2.0-or-later）**，与 Linux 内核所用许可证同源。

```
Copyright (C) 2026 pengshao

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.
```

意味着：可以自由使用、修改、分发；但**分发衍生作品时须以同样的 GPL 条款开放源码**，且不提供任何担保。全文见 [LICENSE](LICENSE)。

---

版本 **2.0.0** ｜ 变更历史见 [CHANGELOG.md](CHANGELOG.md)
*（内容由AI生成，仅供参考）*
*（内容由AI生成，仅供参考）*
