import time
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QLabel, QListWidget, QListWidgetItem, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QTimer
import downloader

class SubscriptionWorker(QThread):
    """Background thread to periodically check subscriptions for new videos."""
    new_video_found = pyqtSignal(str, str) # url, sub_title
    check_finished = pyqtSignal(str, int)  # sub_url, new_count

    def __init__(self, subscriptions, settings):
        super().__init__()
        self.subscriptions = subscriptions
        self.settings = settings
        self.is_running = True

    def run(self):
        while self.is_running:
            for sub in self.subscriptions:
                if not sub.get('enabled', True):
                    continue
                
                url = sub['url']
                print(f"Checking subscription: {url}")
                
                # Fetch info in flat mode to see entries without downloading
                info = downloader.get_video_info(url, **self.settings)
                if info and 'entries' in info:
                    new_count = 0
                    # For each entry, check if it's already in archive.txt
                    # yt-dlp's download_archive handles this, but we want to report count
                    # We'll rely on yt-dlp to skip, but we trigger a download attempt
                    # to let the archive system handle the 'already downloaded' check.
                    
                    # Instead of manual check, we just run the downloader.
                    # yt-dlp with --download-archive will skip existing ones.
                    
                    # We trigger run_multi_download for the channel/playlist
                    downloader.run_multi_download(
                        [url], 
                        **self.settings
                    )
                    # Note: Reporting actual "new" count is tricky without reading archive.txt
                    # For now, we emit that we started checking.
                    self.check_finished.emit(url, 0) # Simplification
            
            # Sleep for 1 hour (default)
            for _ in range(3600):
                if not self.is_running: break
                time.sleep(1)

    def stop(self):
        self.is_running = False

class SubscriptionItem(QFrame):
    remove_requested = pyqtSignal(str)

    def __init__(self, sub_data):
        super().__init__()
        self.url = sub_data['url']
        self.title = sub_data.get('title', self.url)
        self.last_check = sub_data.get('last_check', 'Never')
        self.init_ui()

    def init_ui(self):
        self.setFixedHeight(80)
        self.setStyleSheet("""
            QFrame {
                background-color: #2c2c2e;
                border-radius: 10px;
                padding: 10px;
                border: 1px solid #3a3a3c;
            }
            QLabel { color: white; border: none; }
        """)
        layout = QHBoxLayout(self)

        info_layout = QVBoxLayout()
        self.lbl_title = QLabel(self.title if len(self.title) < 50 else self.title[:47] + "...")
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.lbl_status = QLabel(f"Last check: {self.last_check}")
        self.lbl_status.setStyleSheet("color: #8e8e93; font-size: 11px;")
        
        info_layout.addWidget(self.lbl_title)
        info_layout.addWidget(self.lbl_status)
        layout.addLayout(info_layout, 1)

        self.btn_del = QPushButton("🗑")
        self.btn_del.setFixedSize(35, 35)
        self.btn_del.setStyleSheet("background: transparent; font-size: 16px;")
        self.btn_del.clicked.connect(lambda: self.remove_requested.emit(self.url))
        layout.addWidget(self.btn_del)

class SubscriptionTab(QWidget):
    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.init_ui()
        self.load_subscriptions()
        self.start_background_check()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        header = QLabel("Channel Subscriptions")
        header.setStyleSheet("font-size: 28px; font-weight: 800; color: white;")
        layout.addWidget(header)

        subheader = QLabel("Auto-download new videos from your favorite creators")
        subheader.setStyleSheet("font-size: 14px; color: #8e8e93;")
        layout.addWidget(subheader)

        # Add Subscription Row
        add_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste Channel or Playlist URL...")
        self.url_input.setFixedHeight(45)
        self.url_input.setStyleSheet("""
            QLineEdit {
                background-color: #2c2c2e;
                border: 2px solid #3a3a3c;
                border-radius: 8px;
                color: white;
                padding: 0 12px;
            }
        """)
        add_layout.addWidget(self.url_input)

        self.btn_add = QPushButton("Add Subscription")
        self.btn_add.setFixedHeight(45)
        self.btn_add.setFixedWidth(150)
        self.btn_add.setStyleSheet("""
            QPushButton {
                background-color: #0a84ff;
                color: white;
                border-radius: 8px;
                font-weight: 600;
            }
        """)
        self.btn_add.clicked.connect(self.add_subscription)
        add_layout.addWidget(self.btn_add)
        layout.addLayout(add_layout)

        # List Area
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(self.list_widget)

    def load_subscriptions(self):
        self.list_widget.clear()
        subs = self.config_manager.config.subscriptions
        for sub in subs:
            self._add_item_to_ui(sub)

    def _add_item_to_ui(self, sub_data):
        item = QListWidgetItem(self.list_widget)
        widget = SubscriptionItem(sub_data)
        item.setSizeHint(widget.sizeHint())
        widget.remove_requested.connect(self.remove_subscription)
        self.list_widget.addItem(item)
        self.list_widget.setItemWidget(item, widget)

    def add_subscription(self):
        url = self.url_input.text().strip()
        if not url: return
        
        # Check if already exists
        if any(s['url'] == url for s in self.config_manager.config.subscriptions):
            return

        # Fetch title
        config = self.config_manager.config
        settings = {
            'proxy': config.proxy,
            'cookie_file': config.cookies_file,
            'internal_browser': config.use_internal_browser
        }
        info = downloader.get_video_info(url, **settings)
        title = info.get('title', url) if info else url

        new_sub = {
            'url': url,
            'title': title,
            'last_check': time.strftime("%Y-%m-%d %H:%M"),
            'enabled': True
        }
        
        self.config_manager.config.subscriptions.append(new_sub)
        self.config_manager.save()
        self._add_item_to_ui(new_sub)
        self.url_input.clear()

    @pyqtSlot(str)
    def remove_subscription(self, url):
        subs = self.config_manager.config.subscriptions
        self.config_manager.config.subscriptions = [s for s in subs if s['url'] != url]
        self.config_manager.save()
        self.load_subscriptions()

    def start_background_check(self):
        config = self.config_manager.config
        settings = {
            'download_dir': config.download_folder,
            'proxy': config.proxy,
            'cookie_file': config.cookies_file,
            'internal_browser': config.use_internal_browser
        }
        self.worker = SubscriptionWorker(config.subscriptions, settings)
        self.worker.check_finished.connect(self.update_last_check)
        self.worker.start()

    @pyqtSlot(str, int)
    def update_last_check(self, url, count):
        subs = self.config_manager.config.subscriptions
        timestamp = time.strftime("%Y-%m-%d %H:%M")
        for s in subs:
            if s['url'] == url:
                s['last_check'] = timestamp
        self.config_manager.save()
        self.load_subscriptions()
