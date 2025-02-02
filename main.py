#!/usr/bin/env python3
import sys
from PyQt5.QtWidgets import QApplication

from scraper import DeepSiteScraper
from gui import ResultWindow

def main():
    # Console input prompt
    start_url = input("🌍 Start URL: ").strip()
    search_term = input("🔎 Search term: ").strip()

    # Start scraper
    scraper = DeepSiteScraper(start_url, search_term)
    scraper.crawl()

    if scraper.found:
        print("Matches found. Starting GUI...")
        # Initialize PyQt5 application and show ResultWindow
        app = QApplication(sys.argv)
        resultWindow = ResultWindow(scraper.found, search_term)
        resultWindow.show()
        sys.exit(app.exec_())
    else:
        print("No matches found.")

if __name__ == "__main__":
    main()
