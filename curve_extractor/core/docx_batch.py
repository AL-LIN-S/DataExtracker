from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from pathlib import PurePosixPath
import re
from typing import Callable
from zipfile import ZipFile

import numpy as np
from PIL import Image, ImageOps

from curve_extractor.core.image_kind import is_probably_table_image


_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
_PIC_RE = re.compile(r"\bPic\s*(\d+)\s*:?", re.IGNORECASE)
_STATEMENT_RE = re.compile(r"\bStatement\s*\d*\s*:?", re.IGNORECASE)


@dataclass(frozen=True)
class DocxPlotImage:
    pic_number: int
    image_index: int
    output_stem: str
    statement: str
    media_name: str
    image_rgb: np.ndarray
    statement_image_count: int = 0
    statement_image_media_names: tuple[str, ...] = ()


@dataclass
class _PicGroup:
    pic_number: int
    image_refs: list[str]
    statement_parts: list[str]


StatementImageOCR = Callable[[np.ndarray, str], str]


def iter_docx_plot_images(
    docx_path: str | Path,
    *,
    statement_image_ocr: StatementImageOCR | None = None,
) -> list[DocxPlotImage]:
    from xml.etree import ElementTree as ET

    with ZipFile(docx_path) as archive:
        rels = _read_relationships(archive, ET)
        root = ET.fromstring(archive.read("word/document.xml"))
        groups = _parse_groups(root)
        items: list[DocxPlotImage] = []
        for group in groups:
            plot_images: list[tuple[str, np.ndarray]] = []
            statement_image_names: list[str] = []
            statement_parts = list(group.statement_parts)
            for relationship_id in group.image_refs:
                media_name = _relationship_media_path(rels[relationship_id])
                image_rgb = _read_image_rgb(archive, media_name)
                if is_probably_table_image(image_rgb):
                    statement_image_names.append(media_name)
                    table_text = (statement_image_ocr or _ocr_statement_image)(image_rgb, media_name).strip()
                    if table_text:
                        statement_parts.append(f"[table image {media_name} OCR]\n{table_text}")
                else:
                    plot_images.append((media_name, image_rgb))
            image_count = len(plot_images)
            statement = " ".join(part.strip() for part in statement_parts if part.strip()).strip()
            for image_index, (media_name, image_rgb) in enumerate(plot_images, start=1):
                output_stem = _output_stem(group.pic_number, image_index, image_count)
                items.append(
                    DocxPlotImage(
                        pic_number=group.pic_number,
                        image_index=image_index,
                        output_stem=output_stem,
                        statement=statement,
                        media_name=media_name,
                        image_rgb=image_rgb,
                        statement_image_count=len(statement_image_names),
                        statement_image_media_names=tuple(statement_image_names),
                    )
                )
    return items


def _read_relationships(archive: ZipFile, element_tree_module) -> dict[str, str]:
    root = element_tree_module.fromstring(archive.read("word/_rels/document.xml.rels"))
    relationships: dict[str, str] = {}
    for relationship in root.findall("rel:Relationship", _NS):
        relationships[relationship.attrib["Id"]] = relationship.attrib["Target"]
    return relationships


def _parse_groups(root) -> list[_PicGroup]:
    groups: list[_PicGroup] = []
    current: _PicGroup | None = None
    in_statement = False
    for paragraph in root.findall(".//w:p", _NS):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", _NS)).strip()
        image_refs = [
            blip.attrib[f"{{{_NS['r']}}}embed"]
            for blip in paragraph.findall(".//a:blip", _NS)
            if f"{{{_NS['r']}}}embed" in blip.attrib
        ]
        pic_match = _PIC_RE.search(text)
        if pic_match:
            current = _PicGroup(pic_number=int(pic_match.group(1)), image_refs=[], statement_parts=[])
            groups.append(current)
            in_statement = False
        if current is None:
            continue
        current.image_refs.extend(image_refs)
        statement_match = _STATEMENT_RE.search(text)
        if statement_match:
            in_statement = True
            remainder = _STATEMENT_RE.sub("", text, count=1).strip()
            if remainder:
                current.statement_parts.append(remainder)
            continue
        if in_statement and text:
            current.statement_parts.append(text)
    return [group for group in groups if group.image_refs]


def _relationship_media_path(target: str) -> str:
    path = PurePosixPath(target)
    if path.is_absolute():
        return str(path).lstrip("/")
    return str(PurePosixPath("word") / path)


def _read_image_rgb(archive: ZipFile, media_name: str) -> np.ndarray:
    with Image.open(BytesIO(archive.read(media_name))) as image:
        return np.asarray(image.convert("RGB"), dtype=np.uint8).copy()


def _output_stem(pic_number: int, image_index: int, image_count: int) -> str:
    if image_count <= 1:
        return f"pic_{pic_number:03d}"
    return f"pic_{pic_number:03d}_{image_index:02d}"


def _ocr_statement_image(image_rgb: np.ndarray, media_name: str) -> str:
    try:
        import pytesseract

        from curve_extractor.core.auto_calibration import _resolve_tesseract_command
    except ImportError:
        return f"OCR unavailable for {media_name}"

    tesseract_cmd = _resolve_tesseract_command()
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    image = Image.fromarray(image_rgb)
    texts: list[str] = []
    configs = [
        "--psm 6",
        "--psm 6 -c tessedit_char_whitelist=0123456789.-+HzMW%％",
    ]
    for config in configs:
        try:
            text = pytesseract.image_to_string(image, config=config).strip()
        except Exception as exc:  # noqa: BLE001 - OCR failures should not block curve extraction.
            text = f"OCR failed for {media_name}: {exc}"
        if text:
            texts.append(text)
    table_cells = _ocr_table_cells(image_rgb, pytesseract)
    if table_cells:
        texts.append("Table cell values: " + " ".join(table_cells))
    return "\n".join(texts)


def _ocr_table_cells(image_rgb: np.ndarray, pytesseract) -> list[str]:
    values: list[str] = []
    image = Image.fromarray(image_rgb).convert("L")
    for left, top, right, bottom in _table_cell_boxes(image_rgb):
        if right - left < 8 or bottom - top < 8:
            continue
        cell = image.crop((left + 2, top + 2, right - 2, bottom - 2))
        cell = ImageOps.autocontrast(cell)
        cell = cell.resize((cell.width * 10, cell.height * 10), Image.Resampling.LANCZOS)
        try:
            text = pytesseract.image_to_string(
                cell,
                config="--psm 7 -c tessedit_char_whitelist=0123456789.-+",
            ).strip()
        except Exception:  # noqa: BLE001 - a failed cell should not block the table.
            continue
        cleaned = _clean_cell_number(text)
        if cleaned is not None:
            values.append(cleaned)
    return values


def _table_cell_boxes(image_rgb: np.ndarray) -> list[tuple[int, int, int, int]]:
    gray = image_rgb.astype(np.float32).mean(axis=2)
    dark = gray < 80
    height, width = dark.shape
    x_lines = _line_centers(np.flatnonzero(dark.sum(axis=0) >= height * 0.35))
    y_lines = _line_centers(np.flatnonzero(dark.sum(axis=1) >= width * 0.35))
    if len(x_lines) < 2 or len(y_lines) < 2:
        return []
    return [
        (x_lines[x_index], y_lines[y_index], x_lines[x_index + 1], y_lines[y_index + 1])
        for y_index in range(len(y_lines) - 1)
        for x_index in range(len(x_lines) - 1)
    ]


def _line_centers(candidates: np.ndarray) -> list[int]:
    if candidates.size == 0:
        return []
    centers: list[int] = []
    start = previous = int(candidates[0])
    for value in candidates[1:]:
        current = int(value)
        if current <= previous + 2:
            previous = current
            continue
        centers.append((start + previous) // 2)
        start = previous = current
    centers.append((start + previous) // 2)
    return centers


def _clean_cell_number(text: str) -> str | None:
    match = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", text.replace(" ", ""))
    return match.group(0) if match else None
