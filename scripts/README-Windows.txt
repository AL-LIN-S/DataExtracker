Curve Extractor 0.2.0 for Windows
=================================

Double-click CurveExtractor.exe. Keep this whole folder together: the
_internal directory next to the exe is required.

This is a local desktop tool (MIT). It is not a web app. It does not
upload your plots. It is not 100% accurate. Linear axes and
white-background RGB plots only.

Tesseract is NOT included
-------------------------
Automatic reading of axis tick numbers needs a separate Tesseract OCR
install. This folder does not ship Tesseract and will not claim OCR
works without it.

1. Install: https://github.com/UB-Mannheim/tesseract/wiki
2. Add tesseract.exe to PATH, or set:

   TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

If Tesseract is missing, the GUI shows a banner with the PATH /
TESSERACT_CMD tip. You can still pick the plot box, type X/Y ranges,
detect colors, overlay-check, and export CSV.

Command line (Python checkout, not this exe)
--------------------------------------------
python -m curve_extractor.cli

Rebuild from the source repo
----------------------------
scripts\build_windows.bat

产物会写到 E:\tool\CurveExtractor-0.2.0\

中文摘要
--------
双击 CurveExtractor.exe。请把本文件夹整份保留（_internal 必须和 exe 在一起）。
Tesseract 不打进程序：轴刻度 OCR 需单独安装；没装时窗口会提示 PATH /
TESSERACT_CMD。没有 Tesseract 也能手动框图、填范围、提取曲线。
不是网页版，不准 100%，线性轴、白底彩图。
