from PySide6 import QtCore, QtWidgets

from app.helpers import auth_client
from app.helpers.auth_client import LoginData
from app.ui.widgets.warmup_worker import WarmupResult, WarmupWorker


class LoginDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("登录")
        self.setModal(True)
        self.setFixedWidth(360)
        self._login_ok = False
        self._warmup_ready = False
        self._warmup_result: WarmupResult | None = None
        self._build_ui()
        self._load_saved()
        self._start_warmup()
        QtCore.QTimer.singleShot(0, self._ensure_focus)

    @property
    def pixel_free_worker(self):
        if self._warmup_result:
            return self._warmup_result.pixel_free_worker
        return None

    def _build_ui(self):
        layout = QtWidgets.QVBoxLayout(self)
        form = QtWidgets.QFormLayout()
        self.username_edit = QtWidgets.QLineEdit()
        self.password_edit = QtWidgets.QLineEdit()
        self.password_edit.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.remember_checkbox = QtWidgets.QCheckBox("记住账号")
        form.addRow("账号", self.username_edit)
        form.addRow("密码", self.password_edit)
        form.addRow("", self.remember_checkbox)
        layout.addLayout(form)

        self.status_label = QtWidgets.QLabel("正在预热环境，请稍候...")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        buttons_layout = QtWidgets.QHBoxLayout()
        self.login_button = QtWidgets.QPushButton("登录")
        self.cancel_button = QtWidgets.QPushButton("取消")
        buttons_layout.addWidget(self.login_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

        self.login_button.clicked.connect(self._on_login_clicked)
        self.cancel_button.clicked.connect(self.reject)

    def _load_saved(self):
        saved = auth_client.load_saved_login()
        if saved.username:
            self.username_edit.setText(saved.username)
        if saved.remember and saved.password:
            self.password_edit.setText(saved.password)
            self.remember_checkbox.setChecked(True)

    def _start_warmup(self):
        self.warmup_worker = WarmupWorker(self)
        self.warmup_worker.success.connect(self._on_warmup_success)
        self.warmup_worker.failed.connect(self._on_warmup_failed)
        self.warmup_worker.start()

    def _ensure_focus(self):
        self.raise_()
        self.activateWindow()

    def _on_warmup_success(self, result: WarmupResult):
        self._warmup_ready = True
        self._warmup_result = result
        if self._login_ok:
            self.accept()
        else:
            self.status_label.setText("预热完成，可以登录。")

    def _on_warmup_failed(self, message: str):
        self._warmup_ready = False
        self._warmup_result = None
        self.status_label.setText(f"预热失败：{message}")
        self.login_button.setEnabled(False)

    def _on_login_clicked(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text()
        ok, msg = auth_client.validate_credentials(username, password)
        if not ok:
            self.status_label.setText(msg or "登录失败")
            return
        self._login_ok = True
        remember = self.remember_checkbox.isChecked()
        data = LoginData(username=username, password=password, remember=remember)
        auth_client.save_login(data)
        if self._warmup_ready:
            self.accept()
        else:
            self.status_label.setText("登录成功，正在等待预热完成...")
