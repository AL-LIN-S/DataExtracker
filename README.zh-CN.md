# 工程曲线图数字化工具（CLI + 桌面 GUI）

[English](README.md) | [中文](README.zh-CN.md)

**把彩色工程曲线图提取成 CSV** — 支持命令行和 PySide6 桌面端，并自动生成叠图复核。

适合白底、红/绿/蓝饱和色曲线、黑灰网格、线性坐标的工程图。DOCX 里的说明文字或表格图也可作为校验提示。

![原图与叠图预览](docs/images/03_side_by_side.png)

## 和常见描点工具比，多了什么

- **彩色多曲线**自动候选与绑定  
- **多 Y 轴**支持（自动或手动）  
- **DOCX 批量**（`Pic n` / `Statement n`）  
- 每次导出都带 **overlay / 并排重绘 / 色拟合检查**，方便人工核对  

## 30 秒快速试

需要 Python 3.10+。在仓库根目录：

```bash
python -m venv .venv
source .venv/bin/activate   # Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e .
python -m curve_extractor.cli examples/sample_rgb_plot.png --output extracted.csv
```

**打开 GUI：**

```bash
python -m curve_extractor
```

### 安装 Tesseract（自动识别坐标轴）

需要单独安装 Tesseract，并保证在 `PATH` 里，或设置环境变量 `TESSERACT_CMD`。

| 系统 | 常见装法 |
|---|---|
| Windows | [安装包](https://github.com/UB-Mannheim/tesseract/wiki)，然后 `$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"` |
| macOS | `brew install tesseract` |
| Linux | `sudo apt install tesseract-ocr` |


## Windows 第一次跑通

自动识别坐标轴失败，多半是 Tesseract 没装好。按这个最短路径来：

![Windows 第一次跑通](docs/images/04_windows_first_run.png)

1. 安装 Python 3.10+  
2. 安装 [Windows 版 Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)，把 `tesseract.exe` 加进 `PATH`，或设置：

```powershell
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

3. `python -m pip install -e .`  
4. 打开 GUI：`python -m curve_extractor`。OCR 不准时，可手动框选图区、改坐标范围，照样能提取。  
5. 或跑样例：`python -m curve_extractor.cli examples/sample_rgb_plot.png --output extracted.csv`

演示动图（原图 → 叠图 → 并排复核）：

![演示流程](docs/images/demo_flow.gif)

## 截图

| 原图 | 叠图预览 |
|---|---|
| ![input](docs/images/01_input_plot.png) | ![overlay](docs/images/02_overlay_preview.png) |

更多说明见 [`examples/`](examples/)。

## 常用命令

单图：

```bash
python -m curve_extractor.cli 路径/图.png --output extracted.csv
```

手动指定曲线绑定：

```bash
python -m curve_extractor.cli 路径/图.png \
  --output extracted.csv \
  --series "power:MW:0,235,0:45:right_1"
```

DOCX 批量：

```bash
python -m curve_extractor.cli 路径/summary.docx --output-dir outputs
```

安装后也可使用入口：`curve-extractor`（GUI）、`curve-extractor-cli`（CLI）。

## 隐私与限制

仓库不含私有报告图、DOCX、本地 OCR 或依赖镜像。仅支持线性坐标；OCR 效果依赖清晰度；自动红绿蓝绑定是启发式的，请务必看复核图。

## 许可证

MIT
