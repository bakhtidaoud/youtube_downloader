import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QLineEdit, QFileDialog
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import yt_dlp

class DownloadThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, url, options):
        super().__init__()
        self.url = url
        self.options = options

    def run(self):
        try:
            with yt_dlp.YoutubeDL(self.options) as ydl:
                ydl.download([self.url])
            self.finished.emit(True, "Download successful!")
        except Exception as e:
            self.finished.emit(False, str(e))

class VideoDownloaderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UltraTube Downloader")
        self.setMinimumSize(800, 600)
        
        # Main Widget and Layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(20)

        # Title
        self.title_label = QLabel("UltraTube Downloader")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #1c1c1e;")
        self.layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("Fast, Minimalist, Premium")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setStyleSheet("font-size: 14px; color: #8e8e93;")
        self.layout.addWidget(self.subtitle_label)

        self.layout.addSpacing(20)

        # URL Input
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste YouTube link here...")
        self.url_input.setStyleSheet("""
            QLineEdit {
                padding: 15px;
                font-size: 16px;
                border: 1px solid #d1d1d6;
                border-radius: 12px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border: 2px solid #007aff;
            }
        """)
        self.layout.addWidget(self.url_input)

        # Download Button
        self.download_btn = QPushButton("Download Now")
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #007aff;
                color: white;
                padding: 16px;
                font-size: 18px;
                font-weight: 600;
                border: none;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: #0063cc;
            }
            QPushButton:disabled {
                background-color: #c7c7cc;
            }
        """)
        self.download_btn.clicked.connect(self.start_download)
        self.layout.addWidget(self.download_btn)

        # Status Label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px; color: #3a3a3c;")
        self.layout.addWidget(self.status_label)

        self.layout.addStretch()

        # Footer
        self.footer_label = QLabel("Requires FFmpeg in system PATH")
        self.footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.footer_label.setStyleSheet("font-size: 11px; color: #aeaeb2;")
        self.layout.addWidget(self.footer_label)

        self.ensure_directories()

    def ensure_directories(self):
        dirs = ['downloads', 'assets', 'src', 'tests']
        for d in dirs:
            if not os.path.exists(d):
                os.makedirs(d)

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            self.status_label.setText("⚠️ Please enter a URL")
            return
        
        self.status_label.setText("⏳ Preparing download...")
        self.download_btn.setEnabled(False)
        
        options = {
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
        }
        
        self.thread = DownloadThread(url, options)
        self.thread.finished.connect(self.on_download_finished)
        self.thread.start()

    def on_download_finished(self, success, message):
        self.download_btn.setEnabled(True)
        if success:
            self.status_label.setText(f"✅ {message}")
            self.url_input.clear()
        else:
            self.status_label.setText(f"❌ {message}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # macOS-like styling for all platforms
    app.setStyle("Fusion")
    window = VideoDownloaderApp()
    window.show()
    sys.exit(app.exec())
