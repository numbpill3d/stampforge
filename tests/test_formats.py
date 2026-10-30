import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtWidgets import QApplication

from stampforge import BORDERS, Layer, STYLE_PRESETS, StampForge, _sidebar, apply_border, render_pattern_frames, render_text_frames, save_gif


class FormatTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def window(self):
        window = StampForge(); self.addCleanup(window.close); return window

    def test_format_switch_changes_canvas(self):
        window = self.window()
        self.assertEqual(window._composite().size, (94, 50))
        for key, size in [("blinkie", (150, 20)), ("button", (88, 31)), ("button32", (88, 32))]:
            window.set_format(key)
            self.assertEqual(window._composite().size, size)
        window.undo()
        self.assertEqual(window._composite().size, (88, 31))

    def test_text_layer_rerenders_on_format_switch(self):
        window = self.window()
        layer = Layer("t", "text", style=dict(text="hello", effect="none", motion="scroll left", hold=1))
        window._regenerate(layer); window.layers = [layer]; window.layer_list.addItem(layer.name)
        self.assertEqual(layer.frames[0].width, 94)
        window.set_format("blinkie")
        self.assertEqual(window.layers[0].frames[0].width, 150)

    def test_blink_frames(self):
        frames = render_text_frames(dict(text="hi", effect="blink", hold=3, color="#ff0000"), 150)
        self.assertEqual(len(frames), 6)
        self.assertGreater(frames[0].getchannel("A").getextrema()[1], 0)
        self.assertEqual(frames[3].getchannel("A").getextrema()[1], 0)

    def test_every_effect_and_pattern_renders(self):
        for effect in ["none", "blink", "flash 2 colours", "colour cycle", "rainbow", "sparkle"]:
            for motion in ["none", "scroll left", "scroll right", "wave"]:
                for font in ["pixel (built-in)", "DejaVu Sans"]:
                    frames = render_text_frames(dict(text="ok <3", effect=effect, motion=motion, outline=True, shadow=True, font=font, hold=1), 150)
                    self.assertTrue(frames)
        for pattern in ["solid", "gradient →", "gradient ↓", "stripes", "checker", "glitter", "scanlines", "dots", "stars",
                        "grid", "diagonal", "plaid", "noise", "polka", "sunburst", "halftone"]:
            frames = render_pattern_frames(dict(pattern=pattern), 88, 31)
            self.assertEqual(frames[0].size, (88, 31))

    def test_gif_roundtrip_transparent_keeps_black(self):
        frames = []
        for colour in ("red", "blue"):
            im = Image.new("RGBA", (150, 20), (0, 0, 0, 0))
            im.paste(Image.new("RGBA", (40, 10), colour), (10, 5))
            im.putpixel((60, 10), (0, 0, 0, 255))
            frames.append(im)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "b.gif"; save_gif(frames, path, delay=150)
            gif = Image.open(path)
            self.assertEqual(gif.size, (150, 20)); self.assertEqual(gif.n_frames, 2)
            first = gif.convert("RGBA")
            self.assertEqual(first.getpixel((0, 0))[3], 0)
            self.assertEqual(first.getpixel((60, 10)), (0, 0, 0, 255))
            self.assertEqual(first.getpixel((15, 8))[:3], (255, 0, 0))

    def test_gif_roundtrip_opaque_button(self):
        window = self.window(); window.set_format("button"); window.border = "raised bevel"
        layer = Layer("p", "pattern", style=dict(pattern="stripes", animated=True, hold=1))
        window._regenerate(layer); window.layers = [layer]
        frames = [window._composite(i) for i in range(window.frame_count())]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "b.gif"; save_gif(frames, path)
            gif = Image.open(path)
            self.assertEqual(gif.size, (88, 31)); self.assertEqual(gif.n_frames, 8)
            self.assertEqual(gif.convert("RGBA").getpixel((0, 0)), (255, 255, 255, 255))

    def test_scroll_over_glitter_loops_cleanly(self):
        window = self.window(); window.set_format("blinkie")
        glitter = Layer("g", "pattern", style=dict(pattern="glitter", hold=2)); window._regenerate(glitter)
        text = Layer("t", "text", style=dict(text="i love my cat <3", font="Terminess", size=12, motion="scroll left", hold=2)); window._regenerate(text)
        window.layers = [glitter, text]
        self.assertEqual(window.frame_count() % len(glitter.frames), 0)

    def test_return_in_spinbox_does_not_open_editor(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from unittest import mock
        calls = []
        patcher = mock.patch.object(StampForge, "edit_layer", lambda _self: calls.append(1)); patcher.start(); self.addCleanup(patcher.stop)
        window = self.window(); window.show(); window.activateWindow(); QTest.qWaitForWindowActive(window)
        window.layer_list.setFocus(); QTest.keyClick(window.layer_list, Qt.Key_Return)
        self.assertEqual(calls, [1])  # sanity: Return on the layer list does edit
        calls.clear()
        layer = Layer("t", "text", style=dict(text="hi")); window._regenerate(layer)
        window.layers = [layer]; window.layer_list.addItem(layer.name); window.layer_list.setCurrentRow(0)
        window.w_spin.setFocus(); QTest.keyClick(window.w_spin, Qt.Key_Return)
        self.assertEqual(calls, [])

    def test_format_style_presets_create_editable_backgrounds(self):
        window = self.window()
        for key in ("stamp", "button", "button32", "blinkie"):
            window.set_format(key)
            self.assertGreaterEqual(window.preset_box.count(), 13)
            window.preset_box.setCurrentIndex(0)
            window.apply_preset()
            self.assertEqual(window.layers[0].kind, "pattern")
            self.assertTrue(window.layers[0].name.startswith("background:"))
            self.assertNotEqual(window.border, "none")
            self.assertEqual(window._composite().size, (window.W, window.H))

    def test_file_browser_places_include_computer_root(self):
        urls = [url.toLocalFile() for url in _sidebar()]
        self.assertIn("/", urls)
        self.assertIn(str(Path.home()), urls)
        self.assertEqual(len(urls), len(set(urls)))

    def test_all_border_styles_render_at_stamp_size(self):
        source = Image.new("RGBA", (94, 50), "white")
        for border in BORDERS:
            result = apply_border(source, border, "#ff4fa8")
            self.assertEqual(result.size, (94, 50))


if __name__ == "__main__":
    unittest.main()
