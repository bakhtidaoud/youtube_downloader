import sys
import os
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, 
    QPushButton, QLabel, QLineEdit, QComboBox, QListWidget, 
    QListWidgetItem, QFrame, QProgressBar
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont

# Import our engine
import downloader
from downloader import DownloadProgress

class DownloadWorker(QThread):
    """Threaded worker for yt-dlp to keep UI responsive."""
    progress_updated = pyqtSignal(object) # Emits DownloadProgress object
    finished = pyqtSignal(str) # Emits absolute path to file

    def __init__(self, url, format_id=None, settings=None):
        super().__init__()
        self.url = url
        self.format_id = format_id
        self.settings = settings or {}

    def run(self):
        # The engine's callback pushes data back to this thread's signal
        def internal_callback(prog: DownloadProgress):
            self.progress_updated.emit(prog)

        # Call engine
        downloader.download_item(
            self.url, 
            format_id=self.format_id,
            progress_callback=internal_callback,
            **self.settings
        )
        self.finished.emit("Download Complete")

class ModernDownloadItem(QFrame):
    """Rich widget for individual download tracking."""
    remove_requested = pyqtSignal(object)

    def __init__(self, url):
        super().__init__()
        self.url = url
        self.file_path = None
        
        self.init_ui()

    def init_ui(self):
        self.setFixedHeight(110)
        self.setStyleSheet("""
            QFrame {
                background-color: #2c2c2e;
                border-radius: 12px;
                padding: 10px;
                border: 1px solid #3a3a3c;
            }
            QLabel { color: white; border: none; }
        """)

        layout = QVBoxLayout(self)
        
        # Top Row: Title and Controls
        top_row = QHBoxLayout()
        self.title_label = QLabel(self.url)
        self.title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        top_row.addWidget(self.title_label, 1)

        self.btn_open = QPushButton("📂")
        self.btn_open.setFixedSize(30, 30)
        self.btn_open.setToolTip("Open Folder")
        self.btn_open.setEnabled(False)
        self.btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open.clicked.connect(self.open_folder)
        top_row.addWidget(self.btn_open)

        self.btn_cancel = QPushButton("✕")
        self.btn_cancel.setFixedSize(30, 30)
        self.btn_cancel.setToolTip("Cancel/Remove")
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel.clicked.connect(lambda: self.remove_requested.emit(self))
        top_row.addWidget(self.btn_cancel)

        layout.addLayout(top_row)

        # Progress Bar
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(8)
        self.pbar.setTextVisible(False)
        self.pbar.setStyleSheet("""
            QProgressBar {
                background-color: #3a3a3c;
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #0a84ff;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.pbar)

        # Bottom Row: Stats
        bottom_row = QHBoxLayout()
        self.status_label = QLabel("Initializing...")
        self.status_label.setStyleSheet("font-size: 11px; color: #8e8e93;")
        bottom_row.addWidget(self.status_label)

        bottom_row.addStretch()

        self.stats_label = QLabel("- MB/s | --:--")
        self.stats_label.setStyleSheet("font-size: 11px; color: #8e8e93; font-family: 'Consolas';")
        bottom_row.addWidget(self.stats_label)
        
        layout.addLayout(bottom_row)

    @pyqtSlot(object)
    def update_progress(self, prog: DownloadProgress):
        if prog.status == 'downloading':
            self.title_label.setText(prog.title)
            self.pbar.setValue(int(prog.percentage))
            self.status_label.setText(f"Downloading... {prog.percentage}%")
            self.stats_label.setText(f"{prog.speed} | {prog.eta}")
        elif prog.status == 'finished':
            self.pbar.setValue(100)
            self.status_label.setText("✅ Completed")
            self.stats_label.setText("Saved to downloads/")
            self.btn_open.setEnabled(True)
            if prog.filename:
                self.file_path = prog.filename

    def open_folder(self):
        folder = os.path.abspath("downloads")
        if sys.platform == 'win32':
            os.startfile(folder)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', folder])
        else:
            subprocess.Popen(['xdg-open', folder])

class VideoDownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.workers = {} # Keep track of active threads
        self.setWindowTitle("UltraTube Premium")
        self.setMinimumSize(950, 700)
        self.apply_theme()
        
        # Central Hub
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = QWidget()
        self.sidebar.setFixedWidth(80)
        self.sidebar.setStyleSheet("background-color: #1c1c1e; border-right: 1px solid #2c2c2e;")
        self.main_layout.addWidget(self.sidebar)

        # Content Area
        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(30, 30, 30, 30)
        self.content_layout.setSpacing(25)
        self.main_layout.addWidget(self.content_area)

        # Header
        header_label = QLabel("UltraTube Downloader")
        header_label.setStyleSheet("font-size: 32px; font-weight: 800; color: white;")
        self.content_layout.addWidget(header_label)

        subheader = QLabel("Premium high-fidelity video extraction tool")
        subheader.setStyleSheet("font-size: 14px; color: #8e8e93;")
        self.content_layout.addWidget(subheader)

        # URL Input Section
        input_container = QWidget()
        input_container_layout = QHBoxLayout(input_container)
        input_container_layout.setContentsMargins(0, 0, 0, 0)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste video or playlist URL here...")
        self.url_input.setFixedHeight(55)
        self.url_input.setStyleSheet("""
            QLineEdit {
                background-color: #2c2c2e;
                border: 2px solid #3a3a3c;
                border-radius: 12px;
                padding: 0 15px;
                font-size: 15px;
                color: white;
            }
            QLineEdit:focus {
                border: 2px solid #0a84ff;
            }
        """)
        input_container_layout.addWidget(self.url_input)

        self.paste_btn = QPushButton("Paste Clipboard")
        self.paste_btn.setFixedHeight(55)
        self.paste_btn.setFixedWidth(140)
        self.paste_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.paste_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3c;
                color: white;
                border-radius: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #48484a;
            }
        """)
        self.paste_btn.clicked.connect(self.paste_from_clipboard)
        input_container_layout.addWidget(self.paste_btn)
        self.content_layout.addWidget(input_container)

        # Options Row
        options_layout = QHBoxLayout()
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Best (Auto)", "MP4 Video", "MP3 Audio"])
        self.format_combo.setFixedHeight(45)
        self.format_combo.setFixedWidth(200)
        options_layout.addWidget(self.format_combo)

        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Maximum Quality", "Large (1080p)", "Medium (720p)", "Small (480p)"])
        self.quality_combo.setFixedHeight(45)
        self.quality_combo.setFixedWidth(200)
        options_layout.addWidget(self.quality_combo)
        
        options_layout.addStretch()
        
        self.download_btn = QPushButton("Start Download")
        self.download_btn.setFixedHeight(50)
        self.download_btn.setFixedWidth(180)
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0a84ff, stop:1 #007aff);
                color: white;
                border-radius: 12px;
                font-weight: bold;
                font-size: 15px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #409cff, stop:1 #0a84ff);
            }
        """)
        self.download_btn.clicked.connect(self.start_new_download)
        options_layout.addWidget(self.download_btn)
        self.content_layout.addLayout(options_layout)

        # Downloads List
        self.list_header = QLabel("Active Queue")
        self.list_header.setStyleSheet("font-size: 18px; font-weight: 600; color: white; margin-top: 20px;")
        self.content_layout.addWidget(self.list_header)

        self.downloads_list = QListWidget()
        self.downloads_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.downloads_list.setStyleSheet("""
            QListWidget {
                background-color: transparent;
                border: none;
            }
            QListWidget::item {
                background-color: transparent;
                margin-bottom: 5px;
            }
        """)
        self.content_layout.addWidget(self.downloads_list)

    def apply_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1c1c1e; }
            QComboBox {
                background-color: #2c2c2e;
                border: 2px solid #3a3a3c;
                border-radius: 10px;
                padding-left: 10px;
                color: white;
            }
            QComboBox::drop-down { border: 0px; width: 30px; }
            QComboBox QAbstractItemView {
                background-color: #2c2c2e;
                color: white;
                selection-background-color: #0a84ff;
                border: 1px solid #3a3a3c;
            }
        """)

    def paste_from_clipboard(self):
        self.url_input.setText(QApplication.clipboard().text())

    def start_new_download(self):
        url = self.url_input.text().strip()
        if not url: return

        # 1. Create UI Item
        item = QListWidgetItem(self.downloads_list)
        widget = ModernDownloadItem(url)
        item.setSizeHint(widget.sizeHint())
        self.downloads_list.addItem(item)
        self.downloads_list.setItemWidget(item, widget)
        
        # Connect UI removal
        widget.remove_requested.connect(self.remove_item)

        # 2. Setup Worker
        worker = DownloadWorker(url)
        worker.progress_updated.connect(widget.update_progress)
        self.workers[url] = (worker, item)
        
        worker.start()
        self.url_input.clear()

    @pyqtSlot(object)
    def remove_item(self, widget):
        # Stop worker if active
        if widget.url in self.workers:
            worker, item = self.workers[widget.url]
            worker.terminate() # Force stop for now
            
            # Remove from UI
            row = self.downloads_list.row(item)
            self.downloads_list.takeItem(row)
            del self.workers[widget.url]

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    
    # Ensure downloads dir exists
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
        
    window = VideoDownloaderApp()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Modern font
    default_font = QFont("Segoe UI", 10)
    app.setFont(default_font)
    
    window = VideoDownloaderApp()
    window.show()
    sys.exit(app.exec())
