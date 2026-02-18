import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile
from PyQt6.QtCore import QUrl

class EmbeddedBrowser(QWidget):
    """An embedded browser tab that shares cookies with the downloader."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # Navigation Bar
        self.nav_bar = QWidget()
        self.nav_bar.setFixedHeight(50)
        self.nav_bar.setStyleSheet("""
            QWidget {
                background-color: #2c2c2e;
                border-bottom: 1px solid #3a3a3c;
            }
            QPushButton {
                background-color: transparent;
                color: white;
                font-size: 18px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3a3a3c;
            }
            QLineEdit {
                background-color: #1c1c1e;
                border: 1px solid #3a3a3c;
                border-radius: 6px;
                color: white;
                padding: 4px 10px;
                font-size: 13px;
            }
        """)
        nav_layout = QHBoxLayout(self.nav_bar)
        nav_layout.setContentsMargins(10, 0, 10, 0)

        self.btn_back = QPushButton("‹")
        self.btn_forward = QPushButton("›")
        self.btn_reload = QPushButton("↻")
        
        self.address_bar = QLineEdit()
        self.address_bar.setPlaceholderText("Enter URL or search...")
        self.address_bar.returnPressed.connect(self.navigate_to_url)

        nav_layout.addWidget(self.btn_back)
        nav_layout.addWidget(self.btn_forward)
        nav_layout.addWidget(self.btn_reload)
        nav_layout.addWidget(self.address_bar)

        self.layout.addWidget(self.nav_bar)

        # Web Engine View
        self.browser = QWebEngineView()
        
        # Set up a persistent profile so cookies are saved
        profile = QWebEngineProfile.defaultProfile()
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
        # Use a sub-directory in current folder for cookie storage
        storage_path = os.path.abspath(os.path.join(os.getcwd(), "browser_data"))
        if not os.path.exists(storage_path):
            os.makedirs(storage_path)
        profile.setPersistentStoragePath(storage_path)
        
        self.browser.urlChanged.connect(self.update_address_bar)
        self.browser.load(QUrl("https://www.youtube.com"))
        
        self.btn_back.clicked.connect(self.browser.back)
        self.btn_forward.clicked.connect(self.browser.forward)
        self.btn_reload.clicked.connect(self.browser.reload)

        self.layout.addWidget(self.browser)

        # Footer info
        self.footer = QLabel("💡 Log in here to download your private 'Watch Later' or members-only videos.")
        self.footer.setStyleSheet("background-color: #1c1c1e; color: #8e8e93; font-size: 11px; padding: 5px 15px;")
        self.layout.addWidget(self.footer)

    def navigate_to_url(self):
        u = self.address_bar.text()
        if not u.startswith("http"):
            u = "https://www.google.com/search?q=" + u
        self.browser.setUrl(QUrl(u))

    def update_address_bar(self, q):
        self.address_bar.setText(q.toString())
        self.address_bar.setCursorPosition(0)

    def get_cookie_file_path(self):
        """Returns the path to the cookie storage used by the browser."""
        # Note:yt-dlp has --cookies-from-browser which is preferred
        # But for this embedded one, we point yt-dlp to the actual storage if needed
        return os.path.join(os.getcwd(), "browser_data", "Cookies")
