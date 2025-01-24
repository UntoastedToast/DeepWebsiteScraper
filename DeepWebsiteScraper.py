import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from queue import Queue
import signal
import sys

class DeepSiteScraper:
    def __init__(self, base_url: str, search_term: str):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.search_term = search_term.lower()
        self.session = requests.Session()
        self.session.headers = {'User-Agent': 'Mozilla/5.0'}
        self.found = set()
        self.visited = set()
        self.queue = Queue()
        self.queue.put(base_url)
        self.running = True
        self.timeout = 8
        self.max_pages = 500
        self.banned_extensions = {
            '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.doc', '.docx',
            '.xls', '.xlsx', '.ppt', '.pptx', '.mp3', '.mp4', '.zip',
            '.tar', '.gz', '.exe', '.svg', '.css', '.js', '.ico', '.webp'
        }

        signal.signal(signal.SIGINT, self._exit_gracefully)

    def _exit_gracefully(self, signum, frame):
        print("\n🛑 Tiefenscan wird abgebrochen...")
        self.running = False
        sys.exit(0)

    def _is_valid_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return (
            parsed.netloc == self.domain and
            not any(parsed.path.lower().endswith(ext) for ext in self.banned_extensions) and
            parsed.scheme in ['http', 'https']
        )

    def _fetch(self, url: str) -> str:
        try:
            response = self.session.get(url, timeout=self.timeout)
            content_type = response.headers.get('Content-Type', '').lower()
            
            if 'text/html' not in content_type:
                print(f"⏩ Überspringe Nicht-HTML: {url}")
                return ''
                
            response.raise_for_status()
            return response.text
            
        except Exception as e:
            print(f"⚠️ Fehler bei {url}: {str(e)}")
            return ''

    def _check_content(self, html: str) -> bool:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Entferne Script- und Style-Tags
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
            
        text = soup.get_text().lower()
        return self.search_term in text

    def _extract_links(self, html: str, base_url: str) -> set:
        soup = BeautifulSoup(html, 'html.parser')
        links = set()
        
        for link in soup.find_all('a', href=True):
            absolute_url = urljoin(base_url, link['href']).split('#')[0]
            if self._is_valid_url(absolute_url):
                links.add(absolute_url)
                
        return links

    def crawl(self):
        print(f"\n🔍 Starte Tiefenscan nach '{self.search_term}' auf {self.domain}")
        
        while self.running and not self.queue.empty() and len(self.visited) < self.max_pages:
            current_url = self.queue.get()

            if current_url in self.visited:
                continue
                
            self.visited.add(current_url)
            print(f"🌐 Scanne Seite {len(self.visited)}/{self.max_pages}: {current_url}")

            html = self._fetch(current_url)
            if not html:
                continue

            if self._check_content(html):
                self.found.add(current_url)
                print(f"🎯 Treffer gefunden!")

            # Neue Links zur Warteschlange hinzufügen
            new_links = self._extract_links(html, current_url)
            for link in new_links:
                if link not in self.visited:
                    self.queue.put(link)

if __name__ == "__main__":
    print("🕸️  Vollständiger Website-Scanner")
    print("Drücke STRG+C zum Abbrechen\n")
    
    try:
        url = input("🌍 Start-URL: ").strip()
        term = input("🔎 Suchbegriff: ").strip()
        
        scraper = DeepSiteScraper(url, term)
        scraper.crawl()

        print("\n📊 Endergebnis:")
        print(f"Gescannte Seiten: {len(scraper.visited)}")
        print(f"Maximales Limit: {'Erreicht' if len(scraper.visited) >= scraper.max_pages else 'Nicht erreicht'}")
        
        if scraper.found:
            print("\n✅ Treffer auf folgenden Seiten:")
            for result in scraper.found:
                print(f"  → {result}")
        else:
            print("\n❌ Keine Treffer gefunden")
            
    except Exception as e:
        print(f"❌ Kritischer Fehler: {str(e)}")