from __future__ import annotations

import re
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from lxml import etree


ROOT = Path(r"E:\Demo of GVIM\deer-flow-mainnew")
DOCX = ROOT / "GVIM2.0.docx"
FIGURE_2 = ROOT / "manuscript_assets" / "publication_figures" / "Fig2_benchmark_performance.png"
FIGURE_5 = ROOT / "manuscript_assets" / "publication_figures" / "Fig5_matbench_bandgap_main_case.png"
FIGURE_2_RELATIONSHIP_ID = "rId10"
FIGURE_5_RELATIONSHIP_ID = "rId13"
FIGURE_2_WIDTH_EMU = int(6.25 * 914400)
FIGURE_5_WIDTH_EMU = int(6.35 * 914400)


def resize_figure_2(document_xml: bytes, image_width: int, image_height: int) -> bytes:
    namespaces = {
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    }
    root = etree.fromstring(document_xml)
    blips = root.xpath(
        f'.//a:blip[@r:embed="{FIGURE_2_RELATIONSHIP_ID}"]', namespaces=namespaces
    )
    if len(blips) != 1:
        raise RuntimeError(f"Expected one Figure 2 drawing, found {len(blips)}")

    height_emu = round(FIGURE_2_WIDTH_EMU * image_height / image_width)
    drawing = blips[0]
    while drawing is not None and etree.QName(drawing).localname not in {"inline", "anchor"}:
        drawing = drawing.getparent()
    if drawing is None:
        raise RuntimeError("Could not locate the Figure 2 drawing container")

    extent = drawing.find("wp:extent", namespaces)
    if extent is None:
        raise RuntimeError("Could not locate the Figure 2 Word extent")
    extent.set("cx", str(FIGURE_2_WIDTH_EMU))
    extent.set("cy", str(height_emu))

    for transform_extent in drawing.xpath(".//a:xfrm/a:ext", namespaces=namespaces):
        transform_extent.set("cx", str(FIGURE_2_WIDTH_EMU))
        transform_extent.set("cy", str(height_emu))

    paragraph = drawing
    while paragraph is not None and etree.QName(paragraph).localname != "p":
        paragraph = paragraph.getparent()
    if paragraph is None:
        raise RuntimeError("Could not locate the Figure 2 paragraph")
    paragraph_properties = paragraph.find("w:pPr", namespaces)
    if paragraph_properties is None:
        paragraph_properties = etree.Element(f'{{{namespaces["w"]}}}pPr')
        paragraph.insert(0, paragraph_properties)
    for tag in ("pageBreakBefore", "keepNext", "keepLines"):
        qualified = f'{{{namespaces["w"]}}}{tag}'
        if paragraph_properties.find(qualified) is None:
            paragraph_properties.append(etree.Element(qualified))

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def resize_figure_5(document_xml: bytes, image_width: int, image_height: int) -> bytes:
    namespaces = {
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
        "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    }
    root = etree.fromstring(document_xml)
    blips = root.xpath(
        f'.//a:blip[@r:embed="{FIGURE_5_RELATIONSHIP_ID}"]', namespaces=namespaces
    )
    if len(blips) != 1:
        raise RuntimeError(f"Expected one Figure 5 drawing, found {len(blips)}")
    height_emu = round(FIGURE_5_WIDTH_EMU * image_height / image_width)
    drawing = blips[0]
    while drawing is not None and etree.QName(drawing).localname not in {"inline", "anchor"}:
        drawing = drawing.getparent()
    if drawing is None:
        raise RuntimeError("Could not locate the Figure 5 drawing container")
    extent = drawing.find("wp:extent", namespaces)
    extent.set("cx", str(FIGURE_5_WIDTH_EMU))
    extent.set("cy", str(height_emu))
    for transform_extent in drawing.xpath(".//a:xfrm/a:ext", namespaces=namespaces):
        transform_extent.set("cx", str(FIGURE_5_WIDTH_EMU))
        transform_extent.set("cy", str(height_emu))
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def main() -> None:
    if not DOCX.exists() or not FIGURE_2.exists() or not FIGURE_5.exists():
        raise FileNotFoundError("The manuscript or publication figure source is missing")

    backup = DOCX.with_name(f"GVIM2.0.before_publication_figure_update_{datetime.now():%Y%m%d_%H%M%S}.docx")
    shutil.copy2(DOCX, backup)
    replacement = FIGURE_2.read_bytes()
    from PIL import Image

    with Image.open(FIGURE_2) as image:
        image_width, image_height = image.size
    with Image.open(FIGURE_5) as image:
        figure_5_width, figure_5_height = image.size
    temporary = DOCX.with_suffix(".publication.tmp.docx")

    with zipfile.ZipFile(DOCX, "r") as source, zipfile.ZipFile(
        temporary, "w", zipfile.ZIP_DEFLATED
    ) as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename == "word/media/image3.png":
                data = replacement
            elif item.filename == "word/media/image6.png":
                data = FIGURE_5.read_bytes()
            elif item.filename == "word/document.xml":
                data = resize_figure_2(data, image_width, image_height)
                data = resize_figure_5(data, figure_5_width, figure_5_height)
            elif item.filename == "word/settings.xml":
                settings = data.decode("utf-8")
                settings = re.sub(r"<w:doNotCompressPictures\s*/>", "", settings)
                settings = re.sub(r"<w14:defaultImageDpi[^>]*/>", "", settings)
                settings = settings.replace(
                    "</w:settings>",
                    '<w:doNotCompressPictures/><w14:defaultImageDpi w14:val="600"/></w:settings>',
                )
                data = settings.encode("utf-8")
            target.writestr(item, data)

    temporary.replace(DOCX)
    print(f"Updated: {DOCX}")
    print(f"Backup: {backup}")


if __name__ == "__main__":
    main()
