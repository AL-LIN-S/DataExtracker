<p align="center">
  <img src="docs/images/hero-xhs.png" alt="没有原始数据 / 只有一张图 / 5 步导成 CSV" width="920">
</p>

### 🎬 Demo video · 演示视频

[![Curve Extractor motion demo](docs/media/motion-preview.gif)](https://github.com/AL-LIN-S/DataExtracker/releases/download/v0.2.0/DataExtracker-motion.mp4)

▶ [Watch the 53 s 1080p video with voiceover (MP4)](https://github.com/AL-LIN-S/DataExtracker/releases/download/v0.2.0/DataExtracker-motion.mp4) · [Download v0.2.0](https://github.com/AL-LIN-S/DataExtracker/releases/tag/v0.2.0)


<p align="center">
  <code>本地</code>&nbsp;·&nbsp;<code>开源</code>&nbsp;·&nbsp;<code>不上传</code>&nbsp;·&nbsp;<code>MIT</code>
  <br><br>
  <a href="#中文">中文</a> · <a href="#english">English</a>
  <br><br>
  <img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-yellow">
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img alt="curve-extractor 0.1.0" src="https://img.shields.io/badge/curve--extractor-0.1.0-informational">
</p>

<a id="中文"></a>

# 没有原始数据。只有一张图。5 步导成 CSV。

想对比文献里那条曲线，文章却只给了图。网页描点，一条线做一次还行——同一周第五次对着图点，那不叫工作流。

这页就是把扫描件 / 截图里的**彩色工程曲线**，在自己电脑上提成宽表 CSV 的教程。包名 `curve-extractor` 0.1.0。图不上传。不准 100%。

![从曲线图到 CSV](docs/images/demo_flow.gif)

---

## 5 步

| ① 选图 | ⑤ 叠图复核 | 并排对照 |
|:---:|:---:|:---:|
| ![原图](docs/images/01_input_plot.png) | ![叠图](docs/images/02_overlay_preview.png) | ![并排](docs/images/03_side_by_side.png) |

### ① 选图

白底、彩色曲线、线性坐标最稳。用 [`examples/`](examples/) 里的合成样例练手即可，自己的项目图别往外传。

### ② 定两轴各两点

X、Y 各落到两个已知刻度，把像素换成真实坐标。轴刻度可以自动读——**Tesseract 只认刻度数字，不是「AI 识曲线」**。读不准就手动框图区，手填 x/y 范围，照样能往下走。

Windows 上轴 OCR 失败，多半是 Tesseract 没进 `PATH`：

![Windows 第一次跑通](docs/images/04_windows_first_run.png)

### ③ 识别颜色

曲线按饱和彩色像素提，不是按鼠标一条条描。红 / 绿 / 蓝可以一起做。自动绑色是启发式的，绑错了看叠图，别装没看见。

### ④ 导出 CSV

宽表，一列一条曲线（`x`，后面每一列一条）。能进 Excel，也能给 Python。缺测留空。

单图 CLI **只写出你指定的 CSV**。叠图复核走 **GUI**；DOCX 批量每张会另写 overlay / 并排图。

### ⑤ 叠图复核

把提取结果叠回原图。重合再往下用；飞了就改图区、改范围、改颜色，再导一次。没有叠图核对的数，不要丢进论文。

---

## 会翻车（先看再装）

> **线性轴 only。** 对数轴不做。  
> **白底彩线最稳。** 深色底、灰度扫描、同色缠绕会翻车。  
> **Tesseract = 轴刻度 OCR**，不是 AI 识曲线。  
> **不准 100%。** 像素量化、轴标定、绑色都会有误差。只信叠回去重合的结果。

还支持：多 Y 轴（自动或手动）、DOCX 按 `Pic n` / `Statement n` 批量。不是网页版，没有在线地址。

---

## 30 秒试跑

Python 3.10+。轴自动识别另装 Tesseract。在仓库根目录：

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
source .venv/bin/activate

python -m pip install -U pip
python -m pip install -e .
python -m curve_extractor.cli examples/sample_rgb_plot.png --output extracted.csv
```

打开 GUI：

```bash
python -m curve_extractor
# 或：curve-extractor
```

安装后 CLI 入口也可以是 `curve-extractor-cli`。

### Windows：Tesseract PATH

1. 安装 Python 3.10+。
2. 安装 [Windows 版 Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)，把 `tesseract.exe` 加进 `PATH`，或：

```powershell
$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"
```

3. `python -m pip install -e .`
4. GUI：`python -m curve_extractor`。OCR 不准时手动框选图区、改坐标范围，照样能提取。
5. 或跑样例：`python -m curve_extractor.cli examples/sample_rgb_plot.png --output extracted.csv`

| 系统 | Tesseract |
|---|---|
| Windows | [UB Mannheim 安装包](https://github.com/UB-Mannheim/tesseract/wiki) + `PATH` 或 `TESSERACT_CMD` |
| macOS | `brew install tesseract` |
| Linux | `sudo apt install tesseract-ocr` |

---

## GUI 和 CLI

| | GUI | 单图 CLI | DOCX 批量 |
|---|---|---|---|
| 入口 | `python -m curve_extractor` | `python -m curve_extractor.cli 图.png --output extracted.csv` | `python -m curve_extractor.cli 报告.docx --output-dir outputs` |
| 定轴 | 自动 OCR，或手动框图 / 改范围 | 自动 OCR | 自动 OCR |
| 导出 | CSV + **叠图预览** | **指定的 CSV** | 每张 `pic_NNN.csv` + overlay / 并排 / 色拟合 / metrics |
| 适合 | 要复核、要手改 | 一张图、命令行 | `Pic n` / `Statement n` 那一摞 |

手动指定曲线（自动绑定不对时）：

```bash
python -m curve_extractor.cli path/to/plot.png \
  --output extracted.csv \
  --series "power:MW:0,235,0:45:right_1"
```

`--series` 格式：`NAME:UNIT:R,G,B:TOLERANCE:Y_AXIS`

DOCX 预期结构：

```text
Pic 1:
[曲线图]
Statement 1:
[可选校验文字]

Pic 2:
[曲线图]
[可选表格图]
Statement 2:
[可选校验文字]
```

表格类图片当作说明 / 校验输入，不当曲线图。CSV 宽表形如 `x,frequency_Hz,power_MW,...`。

更完整的中文说明（GUI 逐步、输出文件、测试）：[README.zh-CN.md](README.zh-CN.md)

---

<a id="english"></a>

## English

**No raw data. Only a plot. Five steps to a CSV.**

Curve Extractor (`curve-extractor` 0.1.0) digitizes colored engineering plots into a wide CSV — locally, MIT, nothing uploaded. It is not a web app and it is not 100% accurate.

**Five steps:** pick a plot → pin two points on each axis → detect colors → export CSV → overlay-check.

1. **Pick a plot.** White background, colored traces, linear axes. Dark backgrounds, grayscale scans, and log axes fail. Synthetic samples live in [`examples/`](examples/).
2. **Two points per axis.** Map pixels to real coordinates. Tesseract OCRs **tick labels only** — it does not “AI-read the curve.” If OCR misses, box the plot area and type the ranges.
3. **Detect colors.** Saturated color pixels, not click-tracing. R/G/B can run together. Auto-binding is heuristic; trust the overlay.
4. **Export CSV.** Wide table, one column per series, blanks for missing samples. Single-image CLI writes **only the CSV you asked for**. Overlay review is in the **GUI**; DOCX batch also writes overlay / side-by-side files per picture.
5. **Overlay-check.** If it doesn’t sit on the original trace, fix the plot box, ranges, or colors and export again. Don’t put an unchecked CSV in a paper.

**Will fail:** linear axes only; white + colored lines work best; dark / log / same-color tangles crash; no 100% accuracy.

**30-second try** (Python 3.10+; Tesseract separately for axis OCR):

```bash
python -m pip install -e .
python -m curve_extractor.cli examples/sample_rgb_plot.png --output extracted.csv
python -m curve_extractor   # GUI
```

Windows Tesseract: [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki) then `$env:TESSERACT_CMD = "C:\Program Files\Tesseract-OCR\tesseract.exe"`.

`--series` format: `NAME:UNIT:R,G,B:TOLERANCE:Y_AXIS`. DOCX batch: `--output-dir` and a `Pic n` / `Statement n` layout. License: MIT.
