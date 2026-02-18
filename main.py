import sys
import os
import subprocess
import logging
import logging.handlers
import traceback
import requests
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
    QPushButton, QLabel, QLineEdit, QComboBox, QListWidget, 
    QListWidgetItem, QFrame, QProgressBar, QStackedWidget,
    QSystemTrayIcon, QGraphicsOpacityEffect, QMessageBox, QCheckBox
)

# 0. Constants
CURRENT_VERSION = "1.0.0"
# Replace with your actual GitHub RAW JSON URL
UPDATE_URL = "https://raw.githubusercontent.com/username/repository/main/version.json"

# 1. Setup Logging
log_file = "app.log"
logger = logging.getLogger("UltraTube")
logger.setLevel(logging.DEBUG)
handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=1024*1024*5, backupCount=3)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# 2. Global Exception Handler
def exception_hook(exctype, value, tb):
    """Global exception handler to show error dialogs and log crashes."""
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"Unhandled exception:\n{error_msg}")
    
    # Show user friendly dialog
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Critical)
    msg.setText("Ooops! Something went wrong.")
    msg.setInformativeText("An unexpected error occurred. A report has been saved to the log file.")
    msg.setDetailedText(error_msg)
    msg.setWindowTitle("Fatal Error")
    msg.exec()
    sys.exit(1)

sys.excepthook = exception_hook
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread, pyqtSlot, QPropertyAnimation, QEasingCurve, QRunnable, QThreadPool, QObject, QTimer, QTime, pyqtProperty
from PyQt6.QtGui import QFont, QIcon, QPainter, QPen, QColor, QConicalGradient, QPixmap

import downloader
from downloader import DownloadProgress
from src.config_manager import ConfigManager
from src.settings_dialog import SettingsDialog
from src.browser_tab import EmbeddedBrowser
from src.subscription_tab import SubscriptionTab

class UpdateSignals(QObject):
    """Signals for the UpdateWorker."""
    update_found = pyqtSignal(str, str, str) # version, url, changelog

class MetadataWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, url, settings):
        super().__init__()
        self.url = url
        self.settings = settings
        
    def run(self):
        try:
            info = downloader.get_video_info(self.url, **self.settings)
            if info:
                self.finished.emit(info)
            else:
                self.error.emit("Could not fetch video info.")
        except Exception as e:
            self.error.emit(str(e))

class UpdateWorker(QThread):
    """Checks for updates in the background."""
    def __init__(self, signals):
        super().__init__()
        self.signals = signals

    def run(self):
        try:
            logger.info("Checking for updates...")
            response = requests.get(UPDATE_URL, timeout=10)
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("version")
                download_url = data.get("url")
                changelog = data.get("changelog", "No changelog provided.")
                
                if latest_version and latest_version != CURRENT_VERSION:
                    logger.info(f"Update found: {latest_version}")
                    self.signals.update_found.emit(latest_version, download_url, changelog)
                else:
                    logger.info("Application is up to date.")
        except Exception as e:
            logger.error(f"Failed to check for updates: {e}")

class DownloadSignals(QObject):
    """Signals for the QRunnable worker."""
    progress = pyqtSignal(object)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

class DownloadWorker(QRunnable):
    """Worker runnable for simultaneous downloads."""
    def __init__(self, url, format_id=None, settings=None):
        super().__init__()
        self.url = url
        self.format_id = format_id
        self.settings = settings or {}
        self.signals = DownloadSignals()

    def run(self):
        def internal_callback(prog: DownloadProgress):
            self.signals.progress.emit(prog)

        try:
            downloader.download_item(
                self.url, 
                format_id=self.format_id,
                progress_callback=internal_callback,
                **self.settings
            )
            self.signals.finished.emit("Complete")
        except Exception as e:
            self.signals.error.emit(str(e))

class CircularProgress(QWidget):
    def __init__(self, colors, size=60):
        super().__init__()
        self.setFixedSize(size, size)
        self.colors = colors
        self.value = 0
        self._target = 0
        self.anim = QPropertyAnimation(self, b"progress_val")
        self.anim.setDuration(600)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    @pyqtProperty(float)
    def progress_val(self): return self.value
    @progress_val.setter
    def progress_val(self, v):
        self.value = v
        self.update()

    def set_value(self, val):
        self._target = val
        self.anim.stop()
        self.anim.setEndValue(float(val))
        self.anim.start()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect().adjusted(5, 5, -5, -5)
        accent = self.colors['accent']
        border = self.colors['border']
        
        # Background Circle
        pen = QPen(QColor(border))
        pen.setWidth(6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawEllipse(rect)
        
        # Progress Arc
        grad = QConicalGradient(rect.center(), 90)
        grad.setColorAt(0, QColor(accent))
        grad.setColorAt(1, QColor(self.colors['accent_light']))
        
        pen.setBrush(grad)
        painter.setPen(pen)
        
        span = int(-self.value * 3.6 * 16)
        painter.drawArc(rect, 90 * 16, span)
        
        # Percentage Text
        painter.setPen(QColor(self.colors['text']))
        painter.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, f"{int(self.value)}%")

class ImageLoader(QThread):
    finished = pyqtSignal(bytes)
    def __init__(self, url):
        super().__init__()
        self.url = url
    def run(self):
        try:
            resp = requests.get(self.url, timeout=10)
            if resp.status_code == 200:
                self.finished.emit(resp.content)
        except: pass

class ModernDownloadItem(QFrame):
    remove_requested = pyqtSignal(object)
    finished_successfully = pyqtSignal(str)

    def __init__(self, url, colors, thumbnail_url=None):
        super().__init__()
        self.url = url
        self.colors = colors
        self.thumbnail_url = thumbnail_url
        self.file_path = None
        
        self.init_ui()
        
        if self.thumbnail_url:
            self.loader = ImageLoader(self.thumbnail_url)
            self.loader.finished.connect(self.set_thumbnail)
            self.loader.start()
            
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self.update_pulse)
        self.pulse_val = 0
        self.pulse_dir = 1

    def set_thumbnail(self, data):
        pix = QPixmap()
        pix.loadFromData(data)
        scaled = pix.scaled(140, 80, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        self.thumb_label.setPixmap(scaled)

    def update_pulse(self):
        """Creates a professional 'breathing' effect during metadata fetch."""
        if self.pbar.value() > 0:
            self.pulse_timer.stop()
            self.setStyleSheet(self.card_style(1.0)) # Solid state
            return
            
        self.pulse_val += 0.05 * self.pulse_dir
        if self.pulse_val >= 1.0: self.pulse_dir = -1
        if self.pulse_val <= 0.3: self.pulse_dir = 1
        
        self.setStyleSheet(self.card_style(self.pulse_val))

    def card_style(self, alpha):
        accent = self.colors['accent']
        # Convert hex to RGBA for pulsed border
        r = int(accent[1:3], 16)
        g = int(accent[3:5], 16)
        b = int(accent[5:7], 16)
        
        return f"""
            ModernDownloadItem {{
                background-color: {self.colors['card']};
                border: 1px solid rgba({r}, {g}, {b}, {alpha});
                border-radius: 16px;
                margin-bottom: 8px;
            }}
            QPushButton {{
                background: {self.colors['bg']};
                border: 1px solid {self.colors['border']};
                border-radius: 10px;
                color: {self.colors['text']};
            }}
            QPushButton:hover {{
                background: {accent};
                color: white;
            }}
        """

    def init_ui(self):
        self.setFixedHeight(110)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)

        self.checkbox = QCheckBox()
        self.checkbox.setFixedSize(22, 22)
        self.checkbox.setChecked(True)
        layout.addWidget(self.checkbox)

        # Thumbnail with Rounded Corners Mask
        self.thumb_container = QFrame()
        self.thumb_container.setFixedSize(140, 80)
        self.thumb_container.setStyleSheet(f"background: {self.colors['bg']}; border-radius: 10px;")
        self.thumb_layout = QVBoxLayout(self.thumb_container)
        self.thumb_layout.setContentsMargins(0,0,0,0)
        
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(140, 80)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setStyleSheet("border-radius: 10px;")
        self.thumb_layout.addWidget(self.thumb_label)
        layout.addWidget(self.thumb_container)

        # Info Section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        self.title_label = QLabel(self.url if len(self.url) < 50 else self.url[:47] + "...")
        self.title_label.setStyleSheet("font-size: 15px; font-weight: 700;")
        self.title_label.setWordWrap(True)
        info_layout.addWidget(self.title_label)

        self.status_label = QLabel("Awaiting command...")
        self.status_label.setStyleSheet(f"font-size: 12px; color: {self.colors['sub_text']};")
        info_layout.addWidget(self.status_label)
        
        self.stats_label = QLabel("Ready for extraction")
        self.stats_label.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {self.colors['accent']};")
        info_layout.addWidget(self.stats_label)
        layout.addLayout(info_layout, 1)

        # Circular Progress
        self.pbar = CircularProgress(self.colors, size=70)
        layout.addWidget(self.pbar)

        # Actions
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(5)
        
        self.btn_open = QPushButton("📂")
        self.btn_open.setFixedSize(36, 36)
        self.btn_open.setEnabled(False)
        self.btn_open.clicked.connect(self.open_folder)
        actions_layout.addWidget(self.btn_open)

        self.btn_cancel = QPushButton("✕")
        self.btn_cancel.setFixedSize(36, 36)
        self.btn_cancel.clicked.connect(lambda: self.remove_requested.emit(self))
        actions_layout.addWidget(self.btn_cancel)
        layout.addLayout(actions_layout)

        self.update_style()

    def update_style(self):
        # Initial call
        self.setStyleSheet(self.card_style(1.0))

    def start_pulse(self):
        if not self.pulse_timer.isActive():
            self.pulse_timer.start(50)

    def stop_pulse(self):
        self.pulse_timer.stop()
        self.setStyleSheet(self.card_style(1.0))

    @pyqtSlot(object)
    def update_progress(self, prog: DownloadProgress):
        # Stop pulsing once we have real progress data
        self.stop_pulse()
        
        if prog.title and prog.title != "Unknown":
            self.title_label.setText(prog.title if len(prog.title) < 50 else prog.title[:47] + "...")
        
        self.pbar.set_value(int(prog.percentage))
        self.stats_label.setText(f"{prog.speed} • {prog.eta}")
        
        if prog.status == 'downloading':
            self.status_label.setText("Extracting fidelity layers...")
        elif prog.status == 'finished':
            self.status_label.setText("Archived 🚀")
            self.btn_open.setEnabled(True)
            self.btn_open.setStyleSheet(f"background: {self.colors['success']}; color: white; border: none;")
            self.finished_successfully.emit(prog.title)

    def open_folder(self):
        folder = os.path.abspath("downloads")
        if sys.platform == 'win32': os.startfile(folder)
        else: subprocess.Popen(['open' if sys.platform=='darwin' else 'xdg-open', folder])

class VideoDownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.workers = {}
        self.setWindowTitle("UltraTube Premium")
        self.setMinimumSize(1000, 750)
        
        # Thread Pool for Concurrent Downloads
        self.thread_pool = QThreadPool()
        self.update_thread_limit()
        
        # Scheduler State
        self.pending_queue = []
        self.sched_timer = QTimer(self)
        self.sched_timer.timeout.connect(self.process_scheduled_queue)
        self.sched_timer.start(10000) # Check every 10 seconds
        
        # App Icon
        self.app_icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "resources", "icon.ico"))
        if os.path.exists(self.app_icon_path):
            self.setWindowIcon(QIcon(self.app_icon_path))
        
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(self.app_icon_path) if os.path.exists(self.app_icon_path) else QIcon.fromTheme("download-main"))
        self.tray_icon.show()

        self.init_theme()
        self.init_ui()
        self.center_window()
        self.init_smart_mode()
        
        # Check for Updates
        self.update_signals = UpdateSignals()
        self.update_signals.update_found.connect(self.show_update_dialog)
        self.update_thread = UpdateWorker(self.update_signals)
        self.update_thread.start()

    def show_update_dialog(self, version, url, changelog):
        """Prompt the user when a new update is available."""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Update Available")
        msg.setText(f"A new version of UltraTube is available: <b>v{version}</b>")
        msg.setInformativeText(f"Would you like to download it now?\n\n<b>What's New:</b>\n{changelog}")
        
        yes_btn = msg.addButton("Download Now", QMessageBox.ButtonRole.YesRole)
        msg.addButton("Later", QMessageBox.ButtonRole.NoRole)
        
        msg.exec()
        
        if msg.clickedButton() == yes_btn:
            import webbrowser
            webbrowser.open(url)
            logger.info(f"User accepted update v{version}. Opening: {url}")

    def init_theme(self):
        is_dark = self.config_manager.config.dark_mode
        if is_dark:
            self.colors = {
                'bg': '#0f0f12',         # Deep obsidian
                'sidebar': '#16161a',    # Slightly lighter sidebar
                'card': '#1c1c21',       # Floating cards
                'text': '#f0f0f5',        # Near white
                'sub_text': '#9494a5',   # Muted mauve
                'border': '#2a2a32',     # Subtle separation
                'accent': '#6366f1',     # Vibrant Indigo
                'accent_light': '#818cf8',
                'success': '#10b981',    # Emerald
                'danger': '#ef4444'      # Rose
            }
        else:
            self.colors = {
                'bg': '#f8fafc',         # Clean slate
                'sidebar': '#ffffff',
                'card': '#ffffff',
                'text': '#0f172a',       # Dark slate
                'sub_text': '#64748b',   # Slate gray
                'border': '#e2e8f0',     # Light dividers
                'accent': '#4f46e5',     # Deep Indigo
                'accent_light': '#6366f1',
                'success': '#059669',
                'danger': '#dc2626'
            }

    def init_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(240) # Wider sidebar for premium feel
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(15, 30, 15, 20)
        self.sidebar_layout.setSpacing(10)
        
        app_title = QLabel("UltraTube")
        app_title.setStyleSheet(f"font-size: 22px; font-weight: 900; color: {self.colors['accent']}; margin-bottom: 20px;")
        self.sidebar_layout.addWidget(app_title)

        self.btn_nav_down = self.create_nav_btn("📥  Downloader", 0)
        self.btn_nav_web = self.create_nav_btn("🌐  Browser", 1)
        self.btn_nav_sub = self.create_nav_btn("⭐  Subscriptions", 2)
        
        self.sidebar_layout.addWidget(self.btn_nav_down)
        self.sidebar_layout.addWidget(self.btn_nav_web)
        self.sidebar_layout.addWidget(self.btn_nav_sub)
        self.sidebar_layout.addStretch()
        
        self.btn_report_bug = QPushButton("🐞  Report Issue")
        self.btn_report_bug.setFixedSize(210, 45)
        self.btn_report_bug.setStyleSheet(f"border: 1px solid {self.colors['border']}; font-weight: 600; text-align: left; padding-left: 15px;")
        self.btn_report_bug.clicked.connect(self.report_bug)
        self.sidebar_layout.addWidget(self.btn_report_bug)
        
        self.main_layout.addWidget(self.sidebar)

        # Stack
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)

        # 1. Downloader View (Immediate)
        self.init_downloader_view()
        
        # 2. Lazy Placeholders
        self.browser_view = None
        self.subscription_view = None
        
        # Add placeholders to stack
        self.stack.addWidget(self.download_view)
        
        # We'll add real widgets as indices are accessed
        self.stack.insertWidget(1, QWidget()) # Placeholder for browser
        self.stack.insertWidget(2, QWidget()) # Placeholder for subs

    def init_downloader_view(self):
        self.download_view = QWidget()
        dl_layout = QVBoxLayout(self.download_view)
        dl_layout.setContentsMargins(30, 30, 30, 30)
        dl_layout.setSpacing(20)

        # Header Row
        header_row = QHBoxLayout()
        title_vbox = QVBoxLayout()
        self.lbl_head = QLabel("UltraTube Downloader")
        self.lbl_head.setStyleSheet("font-size: 32px; font-weight: 800;")
        title_vbox.addWidget(self.lbl_head)
        self.lbl_sub = QLabel("Premium high-fidelity video extraction")
        self.lbl_sub.setStyleSheet(f"font-size: 14px; color: {self.colors['sub_text']};")
        title_vbox.addWidget(self.lbl_sub)
        header_row.addLayout(title_vbox)
        header_row.addStretch()
        
        self.btn_theme = QPushButton("🌓")
        self.btn_theme.setFixedSize(40, 40)
        self.btn_theme.clicked.connect(self.toggle_theme)
        header_row.addWidget(self.btn_theme)

        self.smart_btn = QPushButton("✨ Smart Mode")
        self.smart_btn.setFixedSize(140, 40)
        self.smart_btn.clicked.connect(self.toggle_smart_mode)
        header_row.addWidget(self.smart_btn)
        
        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setFixedSize(40, 40)
        self.settings_btn.clicked.connect(self.show_settings)
        header_row.addWidget(self.settings_btn)
        dl_layout.addLayout(header_row)

        # URL Input
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste URL here...")
        self.url_input.setFixedHeight(50)
        dl_layout.addWidget(self.url_input)

        # Options Row
        opt_row = QHBoxLayout()
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Best (Auto)", "MP4 Video", "MP3 Audio"])
        opt_row.addWidget(self.format_combo)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems([
            "Best Available", 
            "8K Ultra HD (4320p)", 
            "4K HDR / 60fps", 
            "4K Ultra HD (2160p)",
            "2K Quad HD (1440p)",
            "Full HD (1080p)", 
            "HD (720p)", 
            "SD (480p)"
        ])
        opt_row.addWidget(self.quality_combo)
        opt_row.addStretch()
        
        self.btn_analyze = QPushButton("Analyze & Add")
        self.btn_analyze.setFixedSize(160, 45)
        self.btn_analyze.setObjectName("download_btn")
        self.btn_analyze.clicked.connect(self.analyze_new_url)
        opt_row.addWidget(self.btn_analyze)
        
        dl_layout.addLayout(opt_row)

        # Batch Controls
        self.batch_layout = QHBoxLayout()
        self.cb_select_all = QCheckBox("Select All")
        self.cb_select_all.setStyleSheet("font-weight: 600; font-size: 13px;")
        self.cb_select_all.setChecked(True)
        self.cb_select_all.clicked.connect(self.toggle_select_all)
        self.batch_layout.addWidget(self.cb_select_all)
        self.batch_layout.addStretch()
        
        self.btn_download_batch = QPushButton("Download Selected")
        self.btn_download_batch.setFixedSize(180, 36)
        self.btn_download_batch.setStyleSheet(f"background-color: {self.colors['accent']}; color: white; border-radius: 10px; font-weight: 700;")
        self.btn_download_batch.clicked.connect(self.start_batch_download)
        self.batch_layout.addWidget(self.btn_download_batch)
        
        dl_layout.addLayout(self.batch_layout)

        self.downloads_list = QListWidget()
        self.downloads_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.downloads_list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.downloads_list.setSpacing(5)
        
        self.stack_dl = QStackedWidget()
        
        self.empty_state = QWidget()
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        empty_icon = QLabel("🚀")
        empty_icon.setStyleSheet("font-size: 64px; margin-bottom: 10px;")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_icon)
        
        empty_title = QLabel("Ready to Download")
        empty_title.setStyleSheet("font-size: 20px; font-weight: 700;")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_title)
        
        empty_desc = QLabel("Paste a URL above to start your high-fidelity extraction journey.")
        empty_desc.setStyleSheet(f"color: {self.colors['sub_text']}; font-size: 14px;")
        empty_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_desc)
        
        self.stack_dl.addWidget(self.empty_state)
        self.stack_dl.addWidget(self.downloads_list)
        dl_layout.addWidget(self.stack_dl)

        self.stack.currentChanged.connect(self.on_stack_changed)
        self.apply_styles()

    def center_window(self):
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        x = (screen.width() - size.width()) // 2
        y = (screen.height() - size.height()) // 2
        self.move(x, y)

    def on_stack_changed(self, index):
        """Lazy load tabs when they are first accessed."""
        if index == 1 and self.browser_view is None:
            logger.info("Lazy loading Embedded Browser...")
            self.browser_view = EmbeddedBrowser()
            self.stack.removeWidget(self.stack.widget(1))
            self.stack.insertWidget(1, self.browser_view)
            self.stack.setCurrentIndex(1)
        elif index == 2 and self.subscription_view is None:
            logger.info("Lazy loading Subscription Tab...")
            self.subscription_view = SubscriptionTab(self.config_manager, self.colors)
            self.stack.removeWidget(self.stack.widget(2))
            self.stack.insertWidget(2, self.subscription_view)
            self.stack.setCurrentIndex(2)
        
        self.update_nav_styles()

    def create_nav_btn(self, text, idx):
        btn = QPushButton(text)
        btn.setFixedSize(210, 45)
        btn.setStyleSheet("text-align: left; padding-left: 15px; font-size: 14px;")
        btn.clicked.connect(lambda: self.stack.setCurrentIndex(idx))
        return btn

    def apply_styles(self):
        accent = self.colors['accent']
        sidebar_bg = self.colors['sidebar']
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {self.colors['bg']}; }}
            QWidget {{ color: {self.colors['text']}; font-family: 'Inter', 'Segoe UI', sans-serif; }}
            
            #sidebar {{ 
                background-color: {sidebar_bg}; 
                border-right: 1px solid {self.colors['border']}; 
            }}
            
            QLineEdit {{ 
                background-color: {self.colors['card']}; 
                border: 2px solid {self.colors['border']}; 
                border-radius: 12px; 
                padding: 12px 20px; 
                font-size: 15px;
                color: {self.colors['text']};
            }}
            QLineEdit:focus {{ border-color: {accent}; background-color: {self.colors['bg']}; }}
            
            QComboBox {{ 
                background-color: {self.colors['card']}; 
                border: 2px solid {self.colors['border']}; 
                border-radius: 12px; 
                padding: 10px 15px; 
                font-size: 14px;
                color: {self.colors['text']};
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox:hover {{ border-color: {accent}; }}
            QComboBox QAbstractItemView {{
                background-color: {self.colors['card']};
                border: 1px solid {self.colors['border']};
                selection-background-color: {accent};
                color: {self.colors['text']};
                outline: none;
            }}

            QCheckBox {{
                spacing: 8px;
                color: {self.colors['text']};
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                background-color: {self.colors['card']};
                border: 2px solid {self.colors['border']};
                border-radius: 6px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {accent};
                border-color: {accent};
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyNCIgaGVpZ2h0PSIyNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjQiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiPjwvcG9seWxpbmU+PC9zdmc+);
            }}
            QCheckBox::indicator:hover {{ border-color: {accent}; }}

            #download_btn {{ 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 {self.colors['accent_light']});
                color: white; 
                border: none; 
                border-radius: 12px;
                font-size: 16px;
                font-weight: 800;
                min-height: 50px;
            }}
            #download_btn:hover {{
                background-color: {self.colors['accent_light']};
            }}

            QProgressBar {{
                border: none;
                background-color: {self.colors['border']};
                height: 8px;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 {self.colors['accent_light']});
                border-radius: 4px;
            }}
            
            QListWidget {{ background: transparent; border: none; outline: none; }}
            QListWidget::item {{ background: transparent; border: none; }}
            QListWidget::item:selected {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 6px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.colors['border']};
                border-radius: 3px;
                min-height: 40px;
            }}
        """)
        self.sidebar.setObjectName("sidebar")
        if hasattr(self, 'download_btn'):
            self.download_btn.setObjectName("download_btn")
        self.update_nav_styles()

    def update_nav_styles(self):
        idx = self.stack.currentIndex()
        btns = [self.btn_nav_down, self.btn_nav_web, self.btn_nav_sub]
        for i, btn in enumerate(btns):
            is_active = (i == idx)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.colors['accent'] if is_active else 'transparent'};
                    color: {'white' if is_active else self.colors['sub_text']};
                    border: none;
                    text-align: left;
                    padding-left: 20px;
                    font-weight: {'800' if is_active else '500'};
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    background-color: {self.colors['accent'] if is_active else self.colors['border']};
                    color: white;
                }}
            """)

    def toggle_theme(self):
        self.config_manager.update(dark_mode=not self.config_manager.config.dark_mode)
        self.init_theme()
        self.apply_styles()

    def show_notification(self, title):
        self.tray_icon.showMessage("Download Finished", title, QSystemTrayIcon.MessageIcon.Information, 3000)

    def is_within_schedule(self):
        config = self.config_manager.config
        if not config.scheduler_enabled:
            return True
        
        now = QTime.currentTime()
        start = QTime.fromString(config.scheduler_start, "HH:mm")
        end = QTime.fromString(config.scheduler_end, "HH:mm")
        
        if start < end:
            return start <= now <= end
        else: # Overnight schedule (e.g. 22:00 to 06:00)
            return now >= start or now <= end

    def process_scheduled_queue(self):
        if self.is_within_schedule() and self.pending_queue:
            while self.pending_queue:
                worker, widget = self.pending_queue.pop(0)
                widget.status_label.setText("Starting scheduled download...")
                widget.start_pulse()
                self.thread_pool.start(worker)

    def analyze_new_url(self):
        url = self.url_input.text().strip()
        if not url: return
        
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.setText("Analyzing...")
        
        config = self.config_manager.config
        settings = {
            'proxy': config.proxy,
            'cookie_file': config.cookies_file,
            'internal_browser': config.use_internal_browser,
            'allow_unplayable': config.experimental_drm,
        }
        
        self.meta_worker = MetadataWorker(url, settings)
        self.meta_worker.finished.connect(self.on_metadata_fetched)
        self.meta_worker.error.connect(self.on_metadata_error)
        self.meta_worker.start()

    def on_metadata_error(self, error):
        logger.error(f"Metadata analysis failed: {error}")
        self.btn_analyze.setEnabled(True)
        self.btn_analyze.setText("Analyze & Add")
        QMessageBox.warning(self, "Analysis Failed", f"Could not analyze URL:\n{error}")

    def on_metadata_fetched(self, info):
        self.btn_analyze.setEnabled(True)
        self.btn_analyze.setText("Analyze & Add")
        self.url_input.clear()
        
        if self.stack_dl.currentIndex() == 0:
            self.stack_dl.setCurrentIndex(1)

        # Handle Playlist vs Single Video
        entries = info.get('entries', [info])
        for entry in entries:
            video_url = entry.get('url') or entry.get('webpage_url')
            if not video_url: continue
            
            title = entry.get('title') or video_url
            thumb = entry.get('thumbnail')
            
            item = QListWidgetItem(self.downloads_list)
            widget = ModernDownloadItem(video_url, self.colors, thumbnail_url=thumb)
            widget.title_label.setText(title if len(title) < 50 else title[:47] + "...")
            widget.status_label.setText("Ready for extraction")
            widget.finished_successfully.connect(self.show_notification)
            item.setSizeHint(widget.sizeHint())
            self.downloads_list.addItem(item)
            self.downloads_list.setItemWidget(item, widget)

    def toggle_select_all(self, checked):
        for i in range(self.downloads_list.count()):
            item = self.downloads_list.item(i)
            widget = self.downloads_list.itemWidget(item)
            if hasattr(widget, 'checkbox'):
                widget.checkbox.setChecked(checked)

    def start_batch_download(self):
        fmt_type = self.format_combo.currentText()
        quality_str = self.quality_combo.currentText()
        engine_format = "bestaudio/best" if fmt_type == "MP3 Audio" else quality_str
        
        config = self.config_manager.config
        settings = {
            'download_dir': config.download_folder,
            'proxy': config.proxy,
            'cookie_file': config.cookies_file,
            'browser': config.browser_cookies if config.browser_cookies != "None" else None,
            'internal_browser': config.use_internal_browser,
            'allow_unplayable': config.experimental_drm,
        }

        count = 0
        for i in range(self.downloads_list.count()):
            item = self.downloads_list.item(i)
            widget = self.downloads_list.itemWidget(item)
            
            if widget.checkbox.isChecked() and widget.pbar.value() == 0:
                worker = DownloadWorker(widget.url, format_id=engine_format, settings=settings)
                worker.signals.progress.connect(widget.update_progress)
                
                widget.start_pulse()
                if self.is_within_schedule():
                    self.thread_pool.start(worker)
                else:
                    self.pending_queue.append((worker, widget))
                    widget.status_label.setText(f"Scheduled...")
                
                widget.checkbox.setEnabled(False) 
                count += 1
        
        if count > 0:
            logger.info(f"Started batch download for {count} items.")

    def report_bug(self):
        """Read logs and provide a way for the user to report issues."""
        try:
            with open("app.log", "r") as f:
                logs = f.read()
            
            # Show a snippet and offer to copy
            msg = QMessageBox(self)
            msg.setWindowTitle("Report a Bug")
            msg.setText("We're sorry you're having issues!")
            msg.setInformativeText("Would you like to copy the last 50 lines of the application log to your clipboard to send to developers?")
            
            last_lines = "\n".join(logs.splitlines()[-50:])
            msg.setDetailedText(last_lines)
            
            copy_btn = msg.addButton("Copy Logs", QMessageBox.ButtonRole.ActionRole)
            msg.addButton(QMessageBox.StandardButton.Close)
            
            msg.exec()
            
            if msg.clickedButton() == copy_btn:
                clipboard = QApplication.clipboard()
                clipboard.setText(logs)
                logger.info("User copied logs to clipboard via report_bug.")
                QMessageBox.information(self, "Success", "Logs have been copied to your clipboard!")
                
        except Exception as e:
            logger.error(f"Failed to read log file: {e}")
            QMessageBox.warning(self, "Error", "Could not read log file.")

    def init_smart_mode(self):
        config = self.config_manager.config
        self.update_smart_ui(config.smart_mode)
        if config.smart_mode:
            idx_fmt = self.format_combo.findText(config.last_format)
            if idx_fmt >= 0: self.format_combo.setCurrentIndex(idx_fmt)
            idx_q = self.quality_combo.findText(config.last_quality)
            if idx_q >= 0: self.quality_combo.setCurrentIndex(idx_q)

    def toggle_smart_mode(self):
        new = not self.config_manager.config.smart_mode
        self.config_manager.update(smart_mode=new)
        self.update_smart_ui(new)

    def update_smart_ui(self, is_on):
        self.smart_btn.setText(f"✨ Smart: {'On' if is_on else 'Off'}")
        self.smart_btn.setStyleSheet(f"background-color: {self.colors['accent'] if is_on else self.colors['card']}; color: {'white' if is_on else self.colors['text']};")

    def update_thread_limit(self):
        limit = self.config_manager.config.max_concurrent
        self.thread_pool.setMaxThreadCount(limit)

    def show_settings(self):
        dialog = SettingsDialog(self.config_manager, self.colors, self)
        if dialog.exec():
            # Refresh if user changed settings
            self.update_thread_limit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = VideoDownloaderApp()
    window.show()
    sys.exit(app.exec())
