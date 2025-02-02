from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem

from .webview import WebView

class ResultWindow(QWidget):
    def __init__(self, found, search_term):
        super().__init__()
        self.found = found  # Dictionary: URL -> Snippets
        self.search_term = search_term
        self.initUI()

    def initUI(self):
        self.setWindowTitle("Found Pages")
        self.setGeometry(100, 100, 400, 300)
        layout = QVBoxLayout()
        label = QLabel("Double-click an entry to open the page:")
        layout.addWidget(label)
        self.listWidget = QListWidget()
        for url in self.found.keys():
            item = QListWidgetItem(url)
            self.listWidget.addItem(item)
        self.listWidget.itemDoubleClicked.connect(self.openWebView)
        layout.addWidget(self.listWidget)
        self.setLayout(layout)

    def openWebView(self, item):
        url = item.text()
        self.webView = WebView(url, self.search_term)
        self.webView.resize(1024, 768)
        self.webView.show()
