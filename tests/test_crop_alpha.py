import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image, ImageDraw
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QListWidgetItem

from stampforge import H, W, Layer, StampForge


class CropAlphaTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_crop_preserves_transparent_template_edges(self):
        window = StampForge()
        self.addCleanup(window.close)
        window.layers = [
            Layer("art", "image", [Image.new("RGBA", (W, H), "red")])
        ]
        window.layer_list.addItem("art")
        window.layer_list.setCurrentRow(0)

        with tempfile.TemporaryDirectory() as temp_dir:
            template_path = Path(temp_dir) / "template.png"
            template = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(template).rectangle(
                (4, 4, W - 5, H - 5), fill="white"
            )
            template.save(template_path)

            item = QListWidgetItem("template")
            item.setData(Qt.UserRole, str(template_path))
            window.template_list.clear()
            window.template_list.addItem(item)
            window.template_list.setCurrentItem(item)
            window.crop_to_template()

        result = window._composite()
        self.assertEqual(result.getpixel((0, 0))[3], 0)
        self.assertEqual(result.getpixel((W // 2, H // 2))[3], 255)

    def test_crop_removes_opaque_paper_gutter_but_keeps_stamp_border(self):
        window = StampForge()
        self.addCleanup(window.close)
        window.layers = [Layer("art", "image", [Image.new("RGBA", (W, H), "red")])]
        window.layer_list.addItem("art")
        window.layer_list.setCurrentRow(0)

        with tempfile.TemporaryDirectory() as temp_dir:
            template_path = Path(temp_dir) / "bordered-template.png"
            template = Image.new("RGBA", (W, H), "white")
            draw = ImageDraw.Draw(template)
            draw.rectangle((6, 6, W - 7, H - 7), outline="black", width=2)
            template.save(template_path)

            item = QListWidgetItem("bordered template")
            item.setData(Qt.UserRole, str(template_path))
            window.template_list.clear()
            window.template_list.addItem(item)
            window.template_list.setCurrentItem(item)
            window.crop_to_template()

        result = window._composite()
        self.assertEqual(result.getpixel((0, 0))[3], 0)
        self.assertEqual(result.getpixel((6, 6))[3], 255)
        self.assertEqual(result.getpixel((W // 2, H // 2))[3], 255)

    def test_crop_removes_thin_white_edge_gutter(self):
        window = StampForge()
        self.addCleanup(window.close)
        window.layers = [Layer("art", "image", [Image.new("RGBA", (W, H), "red")])]
        window.layer_list.addItem("art")
        window.layer_list.setCurrentRow(0)

        with tempfile.TemporaryDirectory() as temp_dir:
            template_path = Path(temp_dir) / "thin-gutter.png"
            template = Image.new("RGBA", (W, H), "white")
            ImageDraw.Draw(template).rectangle((2, 2, W - 3, H - 3), outline="black")
            template.save(template_path)
            item = QListWidgetItem("thin gutter")
            item.setData(Qt.UserRole, str(template_path))
            window.template_list.clear(); window.template_list.addItem(item); window.template_list.setCurrentItem(item)
            window.crop_to_template()

        result = window._composite()
        self.assertEqual(result.getpixel((0, 0))[3], 0)
        self.assertEqual(result.getpixel((2, 2))[3], 255)

