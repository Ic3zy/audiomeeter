import sys
import os
import re
import json
import asyncio
import subprocess
import shutil
import urllib.request

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QApplication,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont


def load_app_version() -> tuple[str, str]:
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        version_file = os.path.join(base_dir, "version.json")
        if os.path.exists(version_file):
            with open(version_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("version", "0.0.127"), data.get("tag_name", "v0.0.127")
    except Exception as e:
        print(f"[AudioMeeter Updater] Error reading version.json: {e}")
    return "0.0.127", "v0.0.127"


APP_VERSION, APP_TAG_NAME = load_app_version()
GITHUB_REPO = "Ic3zy/audiomeeter"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def parse_version(v_str: str) -> tuple:
    match = re.search(r"(\d+(?:\.\d+)+)", str(v_str))
    if match:
        return tuple(int(p) for p in match.group(1).split("."))
    return (0, 0, 0)


def is_debian_based() -> bool:
    if os.path.exists("/etc/debian_version"):
        return True
    if os.path.exists("/etc/os-release"):
        try:
            with open("/etc/os-release", "r", encoding="utf-8") as f:
                content = f.read().lower()
                if any(distro in content for distro in ["debian", "ubuntu", "mint", "pop", "elementary", "zorin"]):
                    return True
        except Exception:
            pass
    if shutil.which("dpkg") or shutil.which("apt"):
        if not shutil.which("pacman"):
            return True
    return False


def build_install_command(tag_name: str, release_body: str) -> str:
    is_deb = is_debian_based()
    bash_blocks = re.findall(r"```bash\s*([\s\S]*?)```", release_body, re.IGNORECASE)

    if is_deb:
        for block in bash_blocks:
            cmd = block.strip()
            if "apt" in cmd or "dpkg" in cmd or ".deb" in cmd:
                clean_cmd = re.sub(r"\bsudo\b\s*", "", cmd).strip()
                return clean_cmd

        download_url = f"https://github.com/{GITHUB_REPO}/releases/download/{tag_name}/audiomeeter-{tag_name}-ubuntu-amd64.deb"
        deb_file = f"audiomeeter-{tag_name}-ubuntu-amd64.deb"
        return f"curl -sSLfO {download_url} && apt install -y ./{deb_file} && rm -f {deb_file}"
    else:
        for block in bash_blocks:
            cmd = block.strip()
            if "pacman" in cmd or ".pkg.tar.zst" in cmd:
                clean_cmd = re.sub(r"\bsudo\b\s*", "", cmd).strip()
                return clean_cmd

        download_url = f"https://github.com/{GITHUB_REPO}/releases/download/{tag_name}/audiomeeter-{tag_name}.pkg.tar.zst"
        pkg_file = f"audiomeeter-{tag_name}.pkg.tar.zst"
        return f"curl -sSLfO {download_url} && pacman -U --noconfirm {pkg_file} && rm -f {pkg_file}"


class CompactUpdateDialog(QDialog):
    def __init__(self, release_info: dict, parent=None):
        super().__init__(parent)
        self.release_info = release_info
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("AudioMeeter - Software Update")
        self.setFixedSize(430, 230)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #243242;
                border: 1px solid #36485c;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QLabel {
                background: transparent;
                color: #e2e8f0;
            }
            QProgressBar {
                border: 1px solid #3a4d63;
                border-radius: 6px;
                text-align: center;
                background-color: #1a2533;
                color: #ffffff;
                font-size: 11px;
                height: 18px;
            }
            QProgressBar::chunk {
                background-color: #00d2ff;
                border-radius: 5px;
            }
            QPushButton#btnUpdate {
                background-color: #00d2ff;
                color: #08131f;
                border: none;
                border-radius: 6px;
                padding: 9px 16px;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton#btnUpdate:hover {
                background-color: #33dcfd;
            }
            QPushButton#btnUpdate:disabled {
                background-color: #2a3b4d;
                color: #64748b;
            }
            QPushButton#btnCancel {
                background-color: #3a4b5c;
                color: #e2e8f0;
                border: none;
                border-radius: 6px;
                padding: 9px 16px;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton#btnCancel:hover {
                background-color: #4a5c6e;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header Title
        title_label = QLabel("New Version Available!")
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #ffffff; background: transparent;")
        layout.addWidget(title_label)

        # Version Info
        self.ver_label = QLabel(
            f"Version: <span style='color:#00d2ff;'>v{APP_VERSION}</span> ➔ <span style='color:#00d2ff;'>{self.release_info['tag_name']}</span>"
        )
        self.ver_label.setStyleSheet(
            "color: #94a3b8; font-size: 12px; background: transparent;"
        )
        layout.addWidget(self.ver_label)

        # Status Label
        self.status_label = QLabel(
            "Click Update Now to automatically download, install, and restart."
        )
        self.status_label.setStyleSheet(
            "color: #cbd5e1; font-size: 11px; background: transparent;"
        )
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        layout.addStretch()

        # Buttons layout
        self.btn_layout = QHBoxLayout()

        self.btn_update = QPushButton("Update Now & Restart")
        self.btn_update.setObjectName("btnUpdate")
        self.btn_update.clicked.connect(self.start_install_process)
        self.btn_layout.addWidget(self.btn_update)

        self.btn_cancel = QPushButton("Later")
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.clicked.connect(self.close)
        self.btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(self.btn_layout)

    def start_install_process(self):
        self.btn_update.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("Authenticating root privileges via Polkit...")

        asyncio.create_task(self._run_root_installer_async())

    async def _run_root_installer_async(self):
        raw_cmd = self.release_info["install_cmd"]
        script_cmd = f"cd /tmp && {raw_cmd}"

        print(
            f"[AudioMeeter Updater] Executing root installation via pkexec: {script_cmd}"
        )

        pkexec_cmd = ["pkexec", "bash", "-c", script_cmd]

        try:
            proc = await asyncio.create_subprocess_exec(
                *pkexec_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                print(
                    "[AudioMeeter Updater] Installation completed successfully with root privileges."
                )
                self.progress_bar.setRange(0, 100)
                self.progress_bar.setValue(100)
                self.status_label.setText(
                    "Update successful! Restarting application..."
                )
                print("[AudioMeeter Updater] Restarting AudioMeeter application...")

                QTimer.singleShot(1200, self.restart_app)
            else:
                err_msg = (
                    stderr.decode("utf-8", errors="ignore").strip()
                    or stdout.decode("utf-8", errors="ignore").strip()
                    or f"Exit code: {proc.returncode}"
                )
                print(f"[AudioMeeter Updater] Root installation failed: {err_msg}")
                self.progress_bar.setVisible(False)
                self.btn_update.setEnabled(True)
                self.btn_cancel.setEnabled(True)
                short_err = err_msg.split("\n")[0]
                self.status_label.setText(f"Update failed: {short_err[:60]}")
        except Exception as e:
            print(f"[AudioMeeter Updater] Subprocess exception: {e}")
            self.progress_bar.setVisible(False)
            self.btn_update.setEnabled(True)
            self.btn_cancel.setEnabled(True)
            self.status_label.setText(f"Update error: {str(e)[:60]}")

    def restart_app(self):
        print(
            "[AudioMeeter Updater] Cleaning up current process and spawning new Python runtime..."
        )

        # Determine executable command
        if os.path.exists("/usr/bin/audiomeeter") and not sys.argv[0].endswith(
            "main.py"
        ):
            cmd = ["/usr/bin/audiomeeter"]
        else:
            cmd = [sys.executable] + sys.argv

        print(f"[AudioMeeter Updater] Launching fresh process: {' '.join(cmd)}")

        subprocess.Popen(cmd, start_new_session=True)

        QApplication.quit()
        sys.exit(0)


def _fetch_release_info_blocking():
    req = urllib.request.Request(
        GITHUB_API_URL, headers={"User-Agent": "AudioMeeter-App"}
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        if response.status == 200:
            return json.loads(response.read().decode("utf-8"))
    return None


def show_update_dialog(release_info: dict, parent_widget=None):
    dialog = CompactUpdateDialog(release_info, parent=parent_widget)
    dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    dialog.show()
    if parent_widget:
        parent_widget._update_dialog_ref = dialog


async def check_for_updates_async(parent_widget=None):
    print(
        f"[AudioMeeter Updater] Checking for updates... (Local version: v{APP_VERSION})"
    )
    try:
        data = await asyncio.to_thread(_fetch_release_info_blocking)
        if not data:
            return

        remote_tag = data.get("tag_name", "")
        remote_ver = parse_version(remote_tag)
        local_ver = parse_version(APP_VERSION)

        print(
            f"[AudioMeeter Updater] GitHub latest release tag: {remote_tag} (Parsed: {remote_ver})"
        )

        if remote_ver > local_ver:
            print(
                f"[AudioMeeter Updater] New update available! (v{APP_VERSION} -> {remote_tag})"
            )
            body = data.get("body", "")

            install_cmd = build_install_command(remote_tag, body)

            release_info = {
                "tag_name": remote_tag,
                "html_url": data.get(
                    "html_url", f"https://github.com/{GITHUB_REPO}/releases/latest"
                ),
                "install_cmd": install_cmd,
            }

            print(
                f"[AudioMeeter Updater] Displaying update dialog ({release_info['tag_name']})..."
            )
            QTimer.singleShot(
                0, lambda: show_update_dialog(release_info, parent_widget)
            )
        else:
            print(
                f"[AudioMeeter Updater] AudioMeeter is up to date (Version: v{APP_VERSION}). No action needed."
            )
    except Exception as e:
        print(f"[AudioMeeter Updater] Update check skipped (Error/Offline): {e}")


def start_update_checker(parent_widget=None):
    def run():
        try:
            asyncio.create_task(check_for_updates_async(parent_widget))
        except Exception as e:
            print(f"[AudioMeeter Updater] Could not schedule update checker: {e}")

    QTimer.singleShot(1000, run)
