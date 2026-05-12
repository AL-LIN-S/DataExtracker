from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
from PIL import Image

from curve_extractor.core.docx_batch import _table_cell_boxes, iter_docx_plot_images


def test_iter_docx_plot_images_groups_images_by_pic_and_uses_table_images_as_statement(tmp_path: Path):
    docx_path = tmp_path / "summary.docx"
    _write_minimal_docx(docx_path)

    items = list(
        iter_docx_plot_images(
            docx_path,
            statement_image_ocr=lambda image, media_name: f"table OCR from {media_name}: 0.25 119.62 108.19",
        )
    )

    assert [item.output_stem for item in items] == ["pic_001", "pic_003_01", "pic_003_02"]
    assert [item.pic_number for item in items] == [1, 3, 3]
    assert [item.image_index for item in items] == [1, 1, 2]
    assert "91.29MW" in items[0].statement
    assert "0.1Hz" in items[1].statement
    assert "table OCR from word/media/image4.png" in items[1].statement
    assert items[1].statement_image_count == 1
    assert items[1].statement_image_media_names == ("word/media/image4.png",)
    assert items[1].statement == items[2].statement
    assert items[0].image_rgb.shape == (6, 8, 3)
    assert items[0].image_rgb.dtype == np.uint8


def test_table_cell_boxes_detects_grid_cells():
    image = np.full((60, 80, 3), 255, dtype=np.uint8)
    image[:, [0, 20, 40, 60, 79]] = 0
    image[[0, 30, 59], :] = 0

    boxes = _table_cell_boxes(image)

    assert boxes == [
        (0, 0, 20, 30),
        (20, 0, 40, 30),
        (40, 0, 60, 30),
        (60, 0, 79, 30),
        (0, 30, 20, 59),
        (20, 30, 40, 59),
        (40, 30, 60, 59),
        (60, 30, 79, 59),
    ]


def _write_minimal_docx(path: Path) -> None:
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
 <w:body>
  <w:p><w:r><w:t>Pic 1:</w:t><w:drawing><a:blip r:embed="rId1"/></w:drawing></w:r></w:p>
  <w:p><w:r><w:t>Statement 1:</w:t></w:r></w:p>
  <w:p><w:r><w:t>Power drops from 91.29MW to 87.44MW.</w:t></w:r></w:p>
  <w:p><w:r><w:t>Pic 3:</w:t><w:drawing><a:blip r:embed="rId2"/></w:drawing></w:r></w:p>
  <w:p><w:r><w:t>60 percent load positive disturbance</w:t></w:r></w:p>
  <w:p><w:r><w:drawing><a:blip r:embed="rId3"/></w:drawing></w:r></w:p>
  <w:p><w:r><w:drawing><a:blip r:embed="rId4"/></w:drawing></w:r></w:p>
  <w:p><w:r><w:t>Statement 3:</w:t></w:r></w:p>
  <w:p><w:r><w:t>Apply 0.1Hz signal and observe the curves.</w:t></w:r></w:p>
 </w:body>
</w:document>
"""
    rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>
 <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image2.png"/>
 <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image3.png"/>
 <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image4.png"/>
</Relationships>
"""
    with ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/_rels/document.xml.rels", rels_xml)
        archive.writestr("word/media/image1.png", _png_bytes((255, 0, 0)))
        archive.writestr("word/media/image2.png", _png_bytes((0, 255, 0)))
        archive.writestr("word/media/image3.png", _png_bytes((0, 0, 255)))
        archive.writestr("word/media/image4.png", _table_png_bytes())


def _png_bytes(color: tuple[int, int, int]) -> bytes:
    image = Image.new("RGB", (8, 6), color)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _table_png_bytes() -> bytes:
    image = Image.new("RGB", (80, 60), "white")
    pixels = image.load()
    for x in range(0, 80, 10):
        for y in range(60):
            pixels[x, y] = (0, 0, 0)
    for y in range(0, 60, 15):
        for x in range(80):
            pixels[x, y] = (0, 0, 0)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
