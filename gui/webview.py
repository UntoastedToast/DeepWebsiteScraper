from PyQt5.QtCore import QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile

from .cookie_interceptor import CookieRequestInterceptor

class WebView(QWebEngineView):
    def __init__(self, url, search_term):
        super().__init__()
        self.search_term = search_term
        
        # Request Interceptor for cookie banner scripts
        profile = QWebEngineProfile.defaultProfile()
        self.interceptor = CookieRequestInterceptor()
        profile.setRequestInterceptor(self.interceptor)
        
        self.load(QUrl(url))
        self.loadFinished.connect(self.on_page_load)

    def on_page_load(self, ok):
        if ok:
            self.highlight_term()
            self.remove_cookie_banners()

    def highlight_term(self):
        js_code = f"""
        (function() {{
            var searchTerm = "{self.search_term}";
            if (!searchTerm) return;
            var regex = new RegExp("("+searchTerm+")", "gi");
            document.body.innerHTML = document.body.innerHTML.replace(regex, "<span style='background-color: yellow;'>$1</span>");
        }})();
        """
        self.page().runJavaScript(js_code)

    def remove_cookie_banners(self):
        js_code = """
        (function() {
            var selectors = [
                '.cookie-banner', '#cookie-consent', '.gdpr-banner',
                '.cc-banner', '.consent-container', 'div[class*="cookie"]',
                'div[id*="cookie"]', 'div[class*="consent"]', 'div[id*="consent"]',
                'div[class*="gdpr"]', 'div[id*="gdpr"]', '.optanon-alert-box-wrapper',
                '#CybotCookiebotDialog', '#cookiescript', '.cookiescript',
                '.cookie-notice', '#cookieNotice', '#cookieLaw', '.cookieAccept',
                '.cookie-container', '.privacy-banner', '.js-cookie-banner',
                '.cookie-popup', '#cookie-banner', '.cookie-message',
                '.cookie-policy', '#gdpr-banner', '.gdpr-notice',
                '.cookie-warning', '.cookie-alert', '.cookie-notification',
                '#cookie-law-info-bar', '.cookie-consent-banner',
                '#onetrust-consent-sdk', '#cookieConsentBanner',
                '.cookiewarning', '.cookie-overlay', '.cookie-disclaimer',
                '.cookie-settings', '#cookie-popup', '.cookie-consent-notice',
                '.eupopup-container', '.cookie-consent-modal',
                // Google specific selectors
                'div[aria-modal="true"]', // Google's consent modal
                'div[aria-label*="cookie"]',
                'div[aria-label*="Cookie"]',
                'div[aria-label*="consent"]',
                'div[aria-label*="Consent"]',
                'form[action*="consent"]',
                '.cookieBar-root', // Google's cookie bar
                '#CXQnmb', // Google's consent dialog
                'div[action*="consent"]',
                '#consent-bump',
                '#consent-page',
                'div[role="dialog"][aria-modal="true"]' // Generic modal that might be cookie consent
            ];
            function removeBanners() {
                selectors.forEach(function(selector) {
                    document.querySelectorAll(selector).forEach(function(element) {
                        element.remove();
                    });
                });
                document.querySelectorAll('iframe').forEach(function(iframe) {
                    if (iframe.src.includes('cookie') || iframe.src.includes('consent')) {
                        iframe.remove();
                    }
                });
            }
            // Initial removal
            removeBanners();
            
            // Also try to click any consent buttons
            function handleConsentButtons() {
                [
                    'button[aria-label*="Accept"]',
                    'button[aria-label*="agree"]',
                    'button[aria-label*="Agree"]',
                    'button:contains("Accept all")',
                    'button:contains("Accept cookies")',
                    'button[jsname="b3VHJd"]', // Google's "Accept all" button
                    'form[action*="consent"] button[type="submit"]'
                ].forEach(selector => {
                    document.querySelectorAll(selector).forEach(button => {
                        try {
                            button.click();
                        } catch (e) {}
                    });
                });
            }
            
            handleConsentButtons();
            // Observe the entire document for new child elements
            var observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === 1) { // Element node
                            // Check if new element or its children match any of the selectors
                            selectors.forEach(function(selector) {
                                if (node.matches(selector) || node.querySelector(selector)) {
                                    removeBanners();
                                    handleConsentButtons();
                                }
                            });
                        }
                    });
                });
            });
            observer.observe(document.body, { childList: true, subtree: true });
        })();
        """
        self.page().runJavaScript(js_code)
