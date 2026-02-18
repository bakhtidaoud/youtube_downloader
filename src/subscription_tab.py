import time
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QLabel, QListWidget, QListWidgetItem, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QTimer, QTime
import downloader

class SubscriptionWorker(QThread):
    """Background thread to periodically check subscriptions for new videos."""
    new_video_found = pyqtSignal(str, str) # url, sub_title
    check_finished = pyqtSignal(str, int)  # sub_url, new_count

    def __init__(self, config_manager, settings):
        super().__init__()
        self.config_manager = config_manager
        self.settings = settings
        self.is_running = True

    def is_within_schedule(self):
        config = self.config_manager.config
        if not config.scheduler_enabled:
            return True
        
        now = QTime.currentTime()
        start = QTime.fromString(config.scheduler_start, "HH:mm")
        end = QTime.fromString(config.scheduler_end, "HH:mm")
        
        if start < end:
            return start <= now <= end
        else: # Overnight
            return now >= start or now <= end

    def run(self):
        while self.is_running:
            # 1. Check Schedule
            if not self.is_within_schedule():
                print("Outside of schedule, waiting 1 minute...")
                time.sleep(60)
                continue

            # 2. Process subs
            for sub in self.config_manager.config.subscriptions:
                if not sub.get('enabled', True):
                    continue
                
                url = sub['url']
                print(f"Checking subscription: {url}")
                
                # Fetch info in flat mode to see entries without downloading
                info = downloader.get_video_info(url, **self.settings)
                if info and 'entries' in info:
                    # We trigger run_multi_download for the channel/playlist
                    downloader.run_multi_download(
                        [url], 
                        **self.settings
                    )
                    self.check_finished.emit(url, 0)
            
            # Sleep for 1 hour (default)
            for _ in range(3600):
                if not self.is_running: break
                time.sleep(1)

    def stop(self):
        self.is_running = False

class AddSubscriptionWorker(QThread):
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
                self.error.emit("Could not fetch channel info.")
        except Exception as e:
            self.error.emit(str(e))

class SubscriptionItem(QFrame):
    remove_requested = pyqtSignal(str)

    def __init__(self, sub_data, colors):
        super().__init__()
        self.url = sub_data['url']
        self.title = sub_data.get('title', self.url)
        self.last_check = sub_data.get('last_check', 'Never')
        self.colors = colors
        self.init_ui()

    def init_ui(self):
        self.setFixedHeight(90)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.colors['card']};
                border-radius: 16px;
                padding: 15px;
                border: 1px solid {self.colors['border']};
            }}
            QFrame:hover {{ border-color: {self.colors['accent']}; }}
        """)
        layout = QHBoxLayout(self)

        info_layout = QVBoxLayout()
        self.lbl_title = QLabel(self.title if len(self.title) < 60 else self.title[:57] + "...")
        self.lbl_title.setStyleSheet(f"font-weight: 700; font-size: 15px; color: {self.colors['text']}; border: none;")
        
        self.lbl_status = QLabel(f"Sync Status: {self.last_check}")
        self.lbl_status.setStyleSheet(f"color: {self.colors['sub_text']}; font-size: 12px; border: none;")
        
        info_layout.addWidget(self.lbl_title)
        info_layout.addWidget(self.lbl_status)
        layout.addLayout(info_layout, 1)

        self.btn_del = QPushButton("🗑")
        self.btn_del.setFixedSize(40, 40)
        self.btn_del.setStyleSheet(f"""
            QPushButton {{ 
                background: transparent; 
                font-size: 18px; 
                color: {self.colors['sub_text']}; 
                border: none;
            }}
            QPushButton:hover {{ color: {self.colors['danger']}; background: {self.colors['bg']}; border-radius: 10px; }}
        """)
        self.btn_del.clicked.connect(lambda: self.remove_requested.emit(self.url))
        layout.addWidget(self.btn_del)

class SubscriptionTab(QWidget):
    def __init__(self, config_manager, colors, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.colors = colors
        self.init_ui()
        self.load_subscriptions()
        self.start_background_check()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)

        header = QLabel("Channel Subscriptions")
        header.setStyleSheet(f"font-size: 32px; font-weight: 800; color: {self.colors['text']};")
        layout.addWidget(header)

        subheader = QLabel("Auto-download new videos from your favorite creators")
        subheader.setStyleSheet(f"font-size: 15px; color: {self.colors['sub_text']};")
        layout.addWidget(subheader)

        # Add Subscription Row
        add_layout = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste Channel or Playlist URL...")
        self.url_input.setFixedHeight(50)
        self.url_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.colors['card']};
                border: 2px solid {self.colors['border']};
                border-radius: 12px;
                color: {self.colors['text']};
                padding: 0 15px;
            }}
            QLineEdit:focus {{ border-color: {self.colors['accent']}; }}
        """)
        add_layout.addWidget(self.url_input)

        self.btn_add = QPushButton("Add Channel")
        self.btn_add.setFixedSize(160, 50)
        self.btn_add.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['accent']};
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: 800;
                font-size: 15px;
            }}
            QPushButton:hover {{ background-color: {self.colors['accent_light']}; }}
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
        widget = SubscriptionItem(sub_data, self.colors)
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

        self.btn_add.setEnabled(False)
        self.btn_add.setText("Wait...")

        config = self.config_manager.config
        settings = {
            'proxy': config.proxy,
            'cookie_file': config.cookies_file,
            'internal_browser': config.use_internal_browser,
            'allow_unplayable': config.experimental_drm,
            'cdm_path': config.cdm_path
        }
        
        self.add_worker = AddSubscriptionWorker(url, settings)
        self.add_worker.finished.connect(self.on_sub_added)
        self.add_worker.error.connect(self.on_sub_error)
        self.add_worker.start()

    def on_sub_error(self, err):
        self.btn_add.setEnabled(True)
        self.btn_add.setText("Add Channel")
        print(f"Sub error: {err}")

    def on_sub_added(self, info):
        self.btn_add.setEnabled(True)
        self.btn_add.setText("Add Channel")
        url = self.url_input.text().strip()
        title = info.get('title', url)
        
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
            'internal_browser': config.use_internal_browser,
            'allow_unplayable': config.experimental_drm,
            'cdm_path': config.cdm_path
        }
        self.worker = SubscriptionWorker(self.config_manager, settings)
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
