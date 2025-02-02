from PyQt5.QtWebEngineCore import QWebEngineUrlRequestInterceptor

class CookieRequestInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self):
        super().__init__()
        self.blocked_domains = [
            'cookiebot.com',
            'consent.cookie-script.com',
            'cdn-cookieyes.com',
            'privacy-mgmt.com',
            'consent.trustarc.com',
            'js.mouseflow.com',
            'cdn.jsdelivr.net/npm/cookieconsent',
            'consent.google.com',
            'consent.youtube.com',
            'consent.google.de'
        ]

    def interceptRequest(self, info):
        url = info.requestUrl().toString()
        if any(domain in url for domain in self.blocked_domains):
            info.block(True)
