#!/usr/bin/env python3
"""StampForge — a tiny 94x50 web-stamp editor."""
from __future__ import annotations

import shutil
import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QAction, QColor, QImage, QPixmap, QIcon
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget, QLineEdit,
)

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
TEMPLATES.mkdir(exist_ok=True)
FILES = ROOT / "files"
FILES.mkdir(exist_ok=True)
ASSET_FOLDERS = {
    "my files": FILES,
    "PNG": Path("/home/scorn/Pictures/GRAPHICS/PNG"),
    "DIV": Path("/home/scorn/Pictures/GRAPHICS/DIV"),
    "GIF": Path("/home/scorn/Pictures/GRAPHICS/GIF"),
    "BACKGROUND TILES": Path("/home/scorn/Pictures/GRAPHICS/BACKGROUND TILES"),
    "FAVICON": Path("/home/scorn/Pictures/GRAPHICS/FAVICON"),
}
IMAGE_EXTENSIONS = {".png", ".gif", ".jpg", ".jpeg", ".webp"}
W, H = 94, 50


@dataclass
class Layer:
    name: str
    kind: str
    frames: list[Image.Image] = field(default_factory=list)
    text: str = ""
    x: int = 0
    y: int = 0
    visible: bool = True


def font(size: int = 10):
    candidates = [
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def pil_to_pixmap(im: Image.Image, scale: int = 8) -> QPixmap:
    rgba = im.convert("RGBA")
    data = rgba.tobytes("raw", "RGBA")
    qimg = QImage(data, rgba.width, rgba.height, QImage.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimg).scaled(W * scale, H * scale, Qt.IgnoreAspectRatio, Qt.FastTransformation)


class StampForge(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StampForge — 94×50 web stamps")
        self.resize(760, 480)
        self.setMinimumSize(700, 440)
        self.setMaximumSize(900, 620)
        self.bg = (245, 245, 240, 255)
        self.layers: list[Layer] = []
        self.frame_index = 0
        self.preview_scale = 8
        self.undo_stack = []
        self.redo_stack = []
        self.timer = QTimer(self)
        self.timer.setInterval(120)
        self.timer.timeout.connect(self._tick)
        self.timer.start()
        self._build_menu()
        self._build_ui()
        self._render()

    def _build_menu(self):
        menu = self.menuBar().addMenu("file")
        for label, fn in [("new stamp", self.new_stamp), ("open image as layer…", self.import_image), ("export PNG…", lambda: self.export("PNG")), ("export GIF…", lambda: self.export("GIF")), ("quit", self.close)]:
            action = QAction(label, self); action.triggered.connect(fn); menu.addAction(action)
        edit = self.menuBar().addMenu("edit")
        undo = QAction("undo   Ctrl+Z", self); undo.triggered.connect(self.undo); edit.addAction(undo)
        redo = QAction("redo   Ctrl+R", self); redo.triggered.connect(self.redo); edit.addAction(redo)
        help_menu = self.menuBar().addMenu("help")
        about = QAction("about StampForge", self); about.triggered.connect(self.about); help_menu.addAction(about)

    def _build_ui(self):
        root = QWidget(); self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(8, 8, 8, 8); outer.setSpacing(8)
        titlebar = QWidget(); titlebar.setObjectName("mac-titlebar"); titlebar.setFixedHeight(27)
        title_row = QHBoxLayout(titlebar); title_row.setContentsMargins(7, 2, 7, 2)
        close_box = QLabel("■"); close_box.setObjectName("mac-close"); title_row.addWidget(close_box)
        title_row.addStretch(); title_row.addWidget(QLabel("StampForge")); title_row.addStretch(); title_row.addWidget(QLabel("94 × 50"))
        outer.addWidget(titlebar)
        body = QWidget(); outer.addWidget(body, 1)
        body_layout = QHBoxLayout(body); body_layout.setContentsMargins(4, 0, 4, 0); body_layout.setSpacing(12)
        left = QVBoxLayout(); body_layout.addLayout(left, 1)
        self.preview = QLabel(); self.preview.setAlignment(Qt.AlignCenter); self.preview.setMinimumSize(360, 260); self.preview.setObjectName("preview")
        left.addWidget(self.preview, 1)
        controls = QHBoxLayout()
        for text, fn in [("import layer", self.import_image), ("add text", self.add_text), ("background", self.pick_bg)]:
            b = QPushButton(text); b.clicked.connect(fn); controls.addWidget(b)
        controls.addStretch(); left.addLayout(controls)
        self.frame_label = QLabel("94 × 50 px  •  frame 1/1  •  live preview")
        left.addWidget(self.frame_label)

        tabs = QTabWidget(); tabs.setFixedWidth(280); body_layout.addWidget(tabs)
        layers_tab = QWidget(); layers_layout = QVBoxLayout(layers_tab)
        self.layer_list = QListWidget(); self.layer_list.currentRowChanged.connect(self._layer_selected); layers_layout.addWidget(self.layer_list)
        row = QHBoxLayout()
        up = QPushButton("↑"); up.clicked.connect(lambda: self.move_layer(-1)); down = QPushButton("↓"); down.clicked.connect(lambda: self.move_layer(1)); remove = QPushButton("remove"); remove.clicked.connect(self.remove_layer)
        row.addWidget(up); row.addWidget(down); row.addWidget(remove); layers_layout.addLayout(row)
        self.vis = QCheckBox("visible"); self.vis.setChecked(True); self.vis.stateChanged.connect(self.toggle_layer); layers_layout.addWidget(self.vis)
        tabs.addTab(layers_tab, "layers")

        templates_tab = QWidget(); tl = QVBoxLayout(templates_tab)
        tl.addWidget(QLabel("drop 94×50 PNG/GIF files in the\ntemplates/ folder, or import one:"))
        self.template_list = QListWidget(); self._style_asset_list(self.template_list); self.template_list.itemDoubleClicked.connect(self.use_template); tl.addWidget(self.template_list)
        imp = QPushButton("import template…"); imp.clicked.connect(self.import_template); tl.addWidget(imp)
        crop = QPushButton("crop to selected template"); crop.clicked.connect(self.crop_to_template); tl.addWidget(crop)
        refresh = QPushButton("refresh folder"); refresh.clicked.connect(self.refresh_templates); tl.addWidget(refresh)
        tabs.addTab(templates_tab, "templates")

        files_tab = QWidget(); fl = QVBoxLayout(files_tab)
        fl.addWidget(QLabel("image folders\nclick a folder to browse its thumbnails"))
        self.folder_list = QListWidget(); self.folder_list.setMaximumHeight(125); self.folder_list.currentItemChanged.connect(self._file_folder_changed); fl.addWidget(self.folder_list)
        self.file_list = QListWidget(); self._style_asset_list(self.file_list); self.file_list.itemDoubleClicked.connect(self.use_file); fl.addWidget(self.file_list)
        add_file = QPushButton("import file…"); add_file.clicked.connect(self.import_file); fl.addWidget(add_file)
        refresh_files = QPushButton("refresh folder"); refresh_files.clicked.connect(self.refresh_files); fl.addWidget(refresh_files)
        tabs.addTab(files_tab, "files")

        self.refresh_templates()
        self.refresh_file_folders()

        settings_tab = QWidget(); form = QFormLayout(settings_tab)
        self.w_spin = QSpinBox(); self.w_spin.setRange(1, 188); self.w_spin.valueChanged.connect(self.resize_layer)
        self.h_spin = QSpinBox(); self.h_spin.setRange(1, 100); self.h_spin.valueChanged.connect(self.resize_layer)
        self.x_spin = QSpinBox(); self.x_spin.setRange(-94, 94); self.x_spin.valueChanged.connect(self.change_position)
        self.y_spin = QSpinBox(); self.y_spin.setRange(-50, 50); self.y_spin.valueChanged.connect(self.change_position)
        form.addRow("width", self.w_spin); form.addRow("height", self.h_spin)
        form.addRow("x", self.x_spin); form.addRow("y", self.y_spin)
        self.loop = QCheckBox("loop animated frames"); self.loop.setChecked(True); form.addRow(self.loop)
        form.addRow(QLabel("export size is always 94 × 50 px"))
        tabs.addTab(settings_tab, "stamp")

    def new_stamp(self):
        self._record()
        self.layers.clear(); self.layer_list.clear(); self.bg = (245, 245, 240, 255); self._render()

    def import_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "choose an image", str(Path.home()), "Images (*.png *.gif *.jpg *.jpeg *.webp)")
        if path: self._add_image(path)

    def _add_image(self, path: str):
        try:
            self._record()
            src = Image.open(path)
            frames = []
            for i in range(getattr(src, "n_frames", 1)):
                src.seek(i); frame = src.convert("RGBA")
                frame.thumbnail((W, H), Image.Resampling.LANCZOS)
                canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0)); canvas.alpha_composite(frame, ((W-frame.width)//2, (H-frame.height)//2)); frames.append(canvas)
            layer = Layer(Path(path).name, "image", frames); self.layers.append(layer)
            self.layer_list.addItem(layer.name); self.layer_list.setCurrentRow(len(self.layers)-1); self._render()
        except Exception as exc:
            QMessageBox.warning(self, "could not import", str(exc))

    def add_text(self):
        text = self._text_dialog()
        if text:
            self._record()
            im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im); d.text((2, 2), text, fill=(16,16,16,255), font=font(10))
            self.layers.append(Layer("text: " + text, "text", [im], text=text)); self.layer_list.addItem(self.layers[-1].name); self.layer_list.setCurrentRow(len(self.layers)-1); self._render()

    def _text_dialog(self):
        box = QMessageBox(self); box.setWindowTitle("add text"); box.setText("type the stamp text")
        field = QLineEdit(box); box.layout().addWidget(field, 1, 1); box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        return field.text() if box.exec() == QMessageBox.Ok else ""

    def pick_bg(self):
        color = QColorDialog.getColor(QColor(*self.bg[:3]), self, "stamp background")
        if color.isValid(): self._record(); self.bg = (color.red(), color.green(), color.blue(), 255); self._render()

    def _layer_selected(self, row):
        if 0 <= row < len(self.layers):
            layer = self.layers[row]; self.vis.blockSignals(True); self.vis.setChecked(layer.visible); self.vis.blockSignals(False)
            self.w_spin.blockSignals(True); self.h_spin.blockSignals(True); self.w_spin.setValue(layer.frames[0].width if layer.frames else W); self.h_spin.setValue(layer.frames[0].height if layer.frames else H); self.w_spin.blockSignals(False); self.h_spin.blockSignals(False)
            self.x_spin.blockSignals(True); self.y_spin.blockSignals(True); self.x_spin.setValue(layer.x); self.y_spin.setValue(layer.y); self.x_spin.blockSignals(False); self.y_spin.blockSignals(False)

    def toggle_layer(self, state):
        row = self.layer_list.currentRow()
        if 0 <= row < len(self.layers): self._record(); self.layers[row].visible = bool(state); self._render()

    def change_position(self):
        row = self.layer_list.currentRow()
        if 0 <= row < len(self.layers): self._record(); self.layers[row].x, self.layers[row].y = self.x_spin.value(), self.y_spin.value(); self._render()

    def resize_layer(self):
        row = self.layer_list.currentRow()
        if not (0 <= row < len(self.layers)): return
        width, height = self.w_spin.value(), self.h_spin.value()
        layer = self.layers[row]
        if layer.frames and layer.frames[0].size == (width, height): return
        self._record()
        layer.frames = [frame.resize((width, height), Image.Resampling.NEAREST) for frame in layer.frames]
        self._render()

    def move_layer(self, delta):
        row = self.layer_list.currentRow(); new = row + delta
        if 0 <= row < len(self.layers) and 0 <= new < len(self.layers):
            self._record()
            self.layers[row], self.layers[new] = self.layers[new], self.layers[row]; item = self.layer_list.takeItem(row); self.layer_list.insertItem(new, item); self.layer_list.setCurrentRow(new); self._render()

    def remove_layer(self):
        row = self.layer_list.currentRow()
        if 0 <= row < len(self.layers): self._record(); self.layers.pop(row); self.layer_list.takeItem(row); self._render()

    def refresh_templates(self):
        self.template_list.clear()
        for p in sorted(TEMPLATES.iterdir()):
            if p.suffix.lower() in {".png", ".gif", ".jpg", ".jpeg", ".webp"}: self._add_asset_item(self.template_list, p)

    def import_template(self):
        path, _ = QFileDialog.getOpenFileName(self, "choose template", str(Path.home()), "Images (*.png *.gif *.jpg *.jpeg *.webp)")
        if path:
            dest = TEMPLATES / Path(path).name; shutil.copy2(path, dest); self.refresh_templates()

    def use_template(self, item): self._add_image(item.data(Qt.UserRole))

    def crop_to_template(self):
        item = self.template_list.currentItem()
        if not item:
            QMessageBox.information(self, "choose a template", "Select a template thumbnail first.")
            return
        path = item.data(Qt.UserRole)
        try:
            template = Image.open(path).convert("RGBA").resize((W, H), Image.Resampling.LANCZOS)
            alpha = template.getchannel("A")
            # Remove paper-colored margins connected to the outside edge. This
            # handles the common stamp-template pattern: a red/black frame,
            # white paper in the middle, and extra white gutters at left/right.
            pix = template.load(); base_alpha = alpha.load(); mask = Image.new("L", (W, H), 255); mask_pix = mask.load()
            corners = [pix[0, 0][:3], pix[W-1, 0][:3], pix[0, H-1][:3], pix[W-1, H-1][:3]]
            bg = max(set(corners), key=corners.count)
            def is_outer_paper(x, y):
                r, g, b, _ = pix[x, y]
                return base_alpha[x, y] > 0 and max(abs(r-bg[0]), abs(g-bg[1]), abs(b-bg[2])) < 32
            queue = deque()
            seen = set()
            for x in range(W): queue.extend([(x, 0), (x, H-1)])
            for y in range(H): queue.extend([(0, y), (W-1, y)])
            while queue:
                x, y = queue.popleft()
                if (x, y) in seen or not (0 <= x < W and 0 <= y < H) or not is_outer_paper(x, y): continue
                seen.add((x, y)); mask_pix[x, y] = 0
                queue.extend(((x+1, y), (x-1, y), (x, y+1), (x, y-1)))
            # If the template has no detectable paper at its perimeter, retain
            # its original alpha instead of making the whole stamp invisible.
            if len(seen) < 4: mask = alpha
            count = max([len(l.frames) for l in self.layers] or [1])
            self._record()
            frames = []
            for index in range(count):
                image = self._composite(index)
                image.putalpha(Image.composite(image.getchannel("A"), Image.new("L", (W, H), 0), mask))
                frames.append(image)
            self.layers = [Layer("cropped: " + Path(path).name, "mask", frames)]
            self.layer_list.clear(); self.layer_list.addItem(self.layers[0].name); self.layer_list.setCurrentRow(0); self._render()
        except Exception as exc:
            QMessageBox.warning(self, "crop failed", str(exc))

    def import_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "choose file", str(Path.home()), "Images (*.png *.gif *.jpg *.jpeg *.webp)")
        if path:
            dest = FILES / Path(path).name; shutil.copy2(path, dest); self.refresh_files()

    def refresh_files(self):
        self._load_file_folder(FILES)

    def refresh_file_folders(self):
        self.folder_list.clear()
        for label, path in ASSET_FOLDERS.items():
            if path.is_dir():
                item = QListWidgetItem(label); item.setData(Qt.UserRole, str(path)); item.setToolTip(str(path)); self.folder_list.addItem(item)
        if self.folder_list.count(): self.folder_list.setCurrentRow(0)

    def _file_folder_changed(self, current, _previous):
        if current: self._load_file_folder(Path(current.data(Qt.UserRole)))

    def _load_file_folder(self, folder):
        self.file_list.clear()
        paths = [p for p in sorted(folder.iterdir()) if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
        shown = paths[:800]
        for p in shown: self._add_asset_item(self.file_list, p)
        suffix = f" (showing first {len(shown)} of {len(paths)})" if len(paths) > len(shown) else ""
        self.file_list.setToolTip(f"{folder}{suffix}")

    def use_file(self, item): self._add_image(item.data(Qt.UserRole))

    def _style_asset_list(self, widget):
        widget.setViewMode(QListWidget.IconMode)
        widget.setIconSize(QSize(94, 50))
        widget.setGridSize(QSize(116, 82))
        widget.setResizeMode(QListWidget.Adjust)
        widget.setMovement(QListWidget.Static)
        widget.setSpacing(4)
        widget.setUniformItemSizes(True)

    def _add_asset_item(self, widget, path):
        pixmap = QPixmap(str(path))
        if pixmap.isNull(): return
        pixmap = pixmap.scaled(94, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        item = QListWidgetItem(QIcon(pixmap), "")
        item.setToolTip(path.name)
        item.setData(Qt.UserRole, str(path))
        widget.addItem(item)

    def _composite(self, frame=0):
        canvas = Image.new("RGBA", (W, H), self.bg)
        for layer in self.layers:
            if not layer.visible or not layer.frames: continue
            src = layer.frames[frame % len(layer.frames)]
            canvas.alpha_composite(src, (layer.x, layer.y))
        return canvas

    def _state(self):
        return (self.bg, [(l.name, l.kind, [f.copy() for f in l.frames], l.text, l.x, l.y, l.visible) for l in self.layers])

    def _record(self):
        self.undo_stack.append(self._state())
        self.redo_stack.clear()
        if len(self.undo_stack) > 40: self.undo_stack.pop(0)

    def _restore(self, state):
        self.bg, raw_layers = state
        self.layers = [Layer(name, kind, [f.copy() for f in frames], text, x, y, visible) for name, kind, frames, text, x, y, visible in raw_layers]
        self.layer_list.clear()
        for layer in self.layers: self.layer_list.addItem(layer.name)
        if self.layers: self.layer_list.setCurrentRow(0)
        self._render()

    def undo(self):
        if not self.undo_stack: return
        self.redo_stack.append(self._state()); self._restore(self.undo_stack.pop())

    def redo(self):
        if not self.redo_stack: return
        self.undo_stack.append(self._state()); self._restore(self.redo_stack.pop())

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_Z: self.undo(); event.accept(); return
        if event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_R: self.redo(); event.accept(); return
        super().keyPressEvent(event)

    def _render(self):
        max_w, max_h = max(200, self.preview.width()-20), max(160, self.preview.height()-20)
        scale = max(1, min(max_w // W, max_h // H)); self.preview_scale = scale
        self.preview.setPixmap(pil_to_pixmap(self._composite(self.frame_index), scale)); count = max([len(l.frames) for l in self.layers] or [1]); self.frame_label.setText(f"94 × 50 px  •  frame {self.frame_index % count + 1}/{count}  •  {scale}× live preview")

    def _tick(self):
        count = max([len(l.frames) for l in self.layers] or [1])
        if count > 1:
            self.frame_index = (self.frame_index + 1) % count
            self._render()

    def resizeEvent(self, event): super().resizeEvent(event); self._render()

    def export(self, kind):
        ext = "gif" if kind == "GIF" else "png"; path, _ = QFileDialog.getSaveFileName(self, f"export {kind}", str(Path.home() / f"stamp.{ext}"), f"{kind} (*.{ext})")
        if not path: return
        count = max([len(l.frames) for l in self.layers] or [1]); frames = [self._composite(i).convert("P", palette=Image.Palette.ADAPTIVE, colors=256) for i in range(count)]
        try:
            if kind == "GIF" and count > 1: frames[0].save(path, save_all=True, append_images=frames[1:], duration=120, loop=0 if self.loop.isChecked() else 1, transparency=0)
            else: frames[0].convert("RGBA").save(path, kind)
            self.statusBar().showMessage(f"saved {path}", 4000)
        except Exception as exc: QMessageBox.warning(self, "export failed", str(exc))

    def about(self): QMessageBox.information(self, "StampForge", "StampForge\nA tiny editor for 94×50 web stamps.\n\nRetro tools for tiny personal websites.")


def main():
    app = QApplication(sys.argv); app.setStyle("Fusion")
    app.setStyleSheet("""
      /* A compact System 7 / early Mac OS palette: graphite, platinum and paper. */
      QWidget { background:#bdbdbd; color:#111; font-family:'Geneva','Charcoal','DejaVu Sans'; font-size:12px; }
      QMainWindow { background:#bdbdbd; }
      QMenuBar { background:#f2f2f2; color:#111; border-bottom:1px solid #111; padding:1px; }
      QMenuBar::item { padding:3px 9px; }
      QMenuBar::item:selected, QMenu::item:selected { background:#111; color:#fff; }
      QMenu { background:#f2f2f2; color:#111; border:1px solid #111; }
      QMenu::item { padding:4px 28px 4px 14px; }
      QPushButton { background:#d7d7d7; border:1px solid #111; border-top-color:#fff; border-left-color:#fff; padding:5px 10px; min-height:22px; }
      QPushButton:hover { background:#e8e8e8; }
      QPushButton:pressed { background:#111; color:#fff; border-color:#111; }
      QListWidget, QLineEdit, QSpinBox { background:#f7f7f2; border:1px solid #111; padding:4px; selection-background-color:#111; selection-color:#fff; }
      QListWidget::item { padding:2px; }
      QTabWidget::pane { border:1px solid #111; background:#d0d0d0; }
      QTabBar::tab { background:#c4c4c4; border:1px solid #111; border-bottom:0; padding:6px 10px; }
      QTabBar::tab:selected { background:#f2f2f2; }
      QGroupBox { border:1px solid #111; margin-top:10px; padding-top:8px; }
      QGroupBox::title { subcontrol-origin:margin; left:8px; padding:0 3px; background:#bdbdbd; }
      QStatusBar { background:#d7d7d7; border-top:1px solid #111; }
      #mac-titlebar { background:#d7d7d7; border:1px solid #111; border-top-color:#fff; border-left-color:#fff; }
      #mac-titlebar QLabel { background:transparent; font-weight:bold; }
      #mac-titlebar #mac-close { border:1px solid #111; padding:0 2px; font-size:8px; }
      #preview { background:#2b2b2b; border:2px solid #111; }
    """)
    win = StampForge(); win.show(); sys.exit(app.exec())


if __name__ == "__main__": main()
