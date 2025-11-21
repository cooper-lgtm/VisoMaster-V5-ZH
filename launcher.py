import logging
import sys

from PySide6 import QtWidgets

from app.helpers.resource_path import appdata_dir, ensure_dll_directory, resource_path


def _setup_logging():
    logs_dir = appdata_dir("VisoMaster") / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    logfile = logs_dir / "app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.FileHandler(logfile, encoding="utf-8")],
    )


def _load_styles(app: QtWidgets.QApplication, ProxyStyle, qdarktheme):
    app.setStyle(ProxyStyle())
    style_file = resource_path("app", "ui", "styles", "dark_styles.qss")
    if style_file.is_file():
        with open(style_file, "r", encoding="utf-8") as f:
            _style = f.read()
        if qdarktheme:
            _style = qdarktheme.load_stylesheet(custom_colors={"primary": "#4facc9"}) + "\n" + _style
        app.setStyleSheet(_style)


def run():
    _setup_logging()
    # Set critical DLL search paths before importing modules that rely on TensorRT/PixelFree.
    dll_dirs = [
        resource_path("dependencies"),
        resource_path("dependencies", "pixel_free"),
        resource_path("TensorRT-10.13.0.35", "bin"),
        resource_path("TensorRT-10.13.0.35", "lib"),
        resource_path("ffmpeg"),
    ]
    for d in dll_dirs:
        ensure_dll_directory(d)

    # Light imports first (avoid heavy MainWindow import before login)
    from app.ui.core.proxy_style import ProxyStyle
    from app.ui.widgets.login_dialog import LoginDialog
    try:
        import qdarktheme
    except Exception:  # pylint: disable=broad-except
        qdarktheme = None

    app = QtWidgets.QApplication(sys.argv)
    _load_styles(app, ProxyStyle, qdarktheme)

    login_dialog = LoginDialog()
    login_dialog.show()
    login_dialog.raise_()
    login_dialog.activateWindow()
    result = login_dialog.exec()
    if result != QtWidgets.QDialog.DialogCode.Accepted:
        sys.exit(0)

    # Import heavy UI only after login accepted
    from app.ui.main_ui import MainWindow

    window = MainWindow(pixel_free_worker=login_dialog.pixel_free_worker)
    window.show()
    window.raise_()
    window.activateWindow()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
