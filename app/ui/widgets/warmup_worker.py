import os
from pathlib import Path
from typing import Optional

from PySide6 import QtCore as qtc

from app.beauty.pixel_free_engine import PixelFreeConfig, PixelFreeError, PixelFreeWorker, build_default_config
from app.helpers.resource_path import ensure_dll_directory, resource_path


class WarmupResult:
    def __init__(self, pixel_free_worker: Optional[PixelFreeWorker] = None, pixel_free_config: Optional[PixelFreeConfig] = None):
        self.pixel_free_worker = pixel_free_worker
        self.pixel_free_config = pixel_free_config


class WarmupWorker(qtc.QThread):
    success = qtc.Signal(object)
    failed = qtc.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dpi_awareness_set = False

    def _prepare_env_paths(self):
        candidate_dirs = [
            resource_path("dependencies"),
            resource_path("dependencies", "pixel_free"),
            resource_path("TensorRT-10.13.0.35"),
            resource_path("tensorrt-engines"),
            resource_path("ffmpeg"),
        ]
        for folder in candidate_dirs:
            ensure_dll_directory(Path(folder))

    def _set_dpi_awareness(self):
        if self._dpi_awareness_set or os.name != "nt":
            return
        try:
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)
            self._dpi_awareness_set = True
        except Exception:
            pass

    def run(self):
        try:
            self._set_dpi_awareness()
            self._prepare_env_paths()
            cfg = build_default_config(resource_path("dependencies", "pixel_free"))
            worker = PixelFreeWorker(cfg)
            self.success.emit(WarmupResult(pixel_free_worker=worker, pixel_free_config=cfg))
        except (PixelFreeError, Exception) as exc:  # pylint: disable=broad-except
            self.failed.emit(str(exc))
