"""
GitHub scanner using Selenium to search for exposed API keys.
"""

import re
import time
from typing import List, Set, Tuple, Optional
from urllib.parse import quote_plus

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from rich.console import Console

console = Console()


class GitHubScanner:
    """Scans GitHub for exposed Google Places API keys."""

    # Google API key patterns
    # Google API keys typically start with 'AIza' and are 39 characters long
    API_KEY_PATTERNS = [
        # Standard Google API key pattern
        r'AIza[0-9A-Za-z\-_]{35}',
        # Quoted API keys
        r'["\']AIza[0-9A-Za-z\-_]{35}["\']',
        # Assignment patterns
        r'(?:api_key|apikey|key|google_api_key|maps_api_key|places_api_key)\s*[=:]\s*["\']?(AIza[0-9A-Za-z\-_]{35})["\']?',
    ]

    # Default search keywords
    DEFAULT_KEYWORDS = [
        "GOOGLE_PLACES_API_KEY",
        "GOOGLE_MAPS_API_KEY",
        "PLACES_API_KEY",
        "MAPS_API_KEY",
        "google_api_key AIza",
        "places_api_key AIza",
        "googleapis.com/maps AIza",
        "maps.googleapis.com key=AIza",
    ]

    # Programming languages to search
    DEFAULT_LANGUAGES = [
        "python",
        "javascript",
        "typescript",
        "java",
        "go",
        "ruby",
        "php",
        "swift",
        "kotlin",
        "dart",
        "rust",
        "c++",
        "c#",
    ]

    def __init__(self, headless: bool = False, debug: bool = False):
        """
        Initialize the GitHub scanner.
        
        Args:
            headless: Run browser in headless mode (no GUI)
            debug: Enable debug output
        """
        self.debug = debug
        self.headless = headless
        self.driver = None
        self.logged_in = False
        self.found_keys: Set[str] = set()

    def _setup_driver(self):
        """Set up the Chrome WebDriver."""
        options = Options()
        
        if self.headless:
            options.add_argument("--headless=new")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # Add user agent to avoid detection
        options.add_argument(
            "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        self.driver = webdriver.Chrome(options=options)
        
        # Additional detection avoidance
        self.driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                """
            },
        )

    def start(self):
        """Start the browser and prompt for GitHub login."""
        console.print("[bold blue]Starting GitHub Scanner...[/bold blue]")
        self._setup_driver()
        
        # Navigate to GitHub login
        console.print("\n[yellow]Please log in to your GitHub account in the browser window.[/yellow]")
        console.print("[yellow]Press Enter after you have logged in...[/yellow]\n")
        
        self.driver.get("https://github.com/login")
        
        # Wait for user to log in
        input()
        
        # Verify login
        self.driver.get("https://github.com")
        time.sleep(2)
        
        try:
            # Check for user avatar or profile menu
            self.driver.find_element(By.CSS_SELECTOR, "img.avatar")
            self.logged_in = True
            console.print("[bold green]✓ Successfully logged in to GitHub[/bold green]\n")
        except NoSuchElementException:
            console.print("[bold red]✗ Login verification failed. Please try again.[/bold red]")
            self.logged_in = False

    def search(
        self,
        keywords: List[str] = None,
        languages: List[str] = None,
        from_iter: int = 0,
        max_pages: int = 5
    ) -> List[Tuple[str, str, str, str]]:
        """
        Search GitHub for API keys.
        
        Args:
            keywords: Search keywords (uses defaults if None)
            languages: Programming languages to filter (uses defaults if None)
            from_iter: Start from specific iteration
            max_pages: Maximum pages to scan per keyword/language combo
            
        Returns:
            List of tuples: (api_key, source_url, file_path, language)
        """
        if not self.logged_in:
            console.print("[bold red]Not logged in. Please call start() first.[/bold red]")
            return []
        
        keywords = keywords or self.DEFAULT_KEYWORDS
        languages = languages or self.DEFAULT_LANGUAGES
        
        results = []
        iteration = 0
        
        total_iterations = len(keywords) * len(languages) * max_pages
        console.print(f"[bold]Total iterations to scan: {total_iterations}[/bold]\n")
        
        for keyword in keywords:
            for language in languages:
                for page in range(1, max_pages + 1):
                    iteration += 1
                    
                    if iteration < from_iter:
                        continue
                    
                    console.print(
                        f"[cyan]Iteration {iteration}/{total_iterations}[/cyan] - "
                        f"Keyword: '{keyword}', Language: {language}, Page: {page}"
                    )
                    
                    try:
                        page_results = self._search_page(keyword, language, page)
                        results.extend(page_results)
                        
                        if len(page_results) == 0:
                            if self.debug:
                                console.print("[dim]No results on this page, moving to next combo[/dim]")
                            break
                        
                        # Rate limiting - be nice to GitHub
                        time.sleep(3)
                        
                    except Exception as e:
                        console.print(f"[red]Error during search: {e}[/red]")
                        time.sleep(5)
        
        return results

    def _search_page(
        self,
        keyword: str,
        language: str,
        page: int
    ) -> List[Tuple[str, str, str, str]]:
        """
        Search a single page of GitHub results.
        
        Returns:
            List of tuples: (api_key, source_url, file_path, language)
        """
        results = []
        
        # Build search URL
        # Using GitHub code search with regex support
        encoded_keyword = quote_plus(keyword)
        search_url = (
            f"https://github.com/search?q={encoded_keyword}"
            f"+language%3A{language}&type=code&p={page}"
        )
        
        if self.debug:
            console.print(f"[dim]Navigating to: {search_url}[/dim]")
        
        self.driver.get(search_url)
        
        # Wait for results to load
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='results-list']"))
            )
        except TimeoutException:
            # No results or page didn't load
            if self.debug:
                console.print("[dim]Timeout waiting for results[/dim]")
            return []
        
        time.sleep(2)  # Additional wait for dynamic content
        
        # Get all code snippets
        try:
            code_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                "[data-testid='results-list'] .code-list .f4"
            )
            
            # Fallback to other selectors if the above doesn't work
            if not code_elements:
                code_elements = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    ".code-list td.blob-code"
                )
            
            if not code_elements:
                # Try another common structure
                code_elements = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "[data-hovercard-type='repository'] + div pre"
                )
            
            # Also get the page source for regex matching
            page_source = self.driver.page_source
            
            # Extract API keys using regex patterns
            for pattern in self.API_KEY_PATTERNS:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                for match in matches:
                    # Clean up the key (remove quotes if present)
                    key = match.strip("'\"")
                    
                    # Ensure it matches the standard format
                    if re.match(r'^AIza[0-9A-Za-z\-_]{35}$', key):
                        if key not in self.found_keys:
                            self.found_keys.add(key)
                            results.append((key, search_url, "", language))
                            console.print(f"[bold green]Found key: {key[:20]}...[/bold green]")
            
            # Also try to get file paths from result items
            result_items = self.driver.find_elements(
                By.CSS_SELECTOR,
                "[data-testid='results-list'] > div"
            )
            
            for item in result_items:
                try:
                    # Get file path link
                    file_link = item.find_element(By.CSS_SELECTOR, "a[href*='/blob/']")
                    file_url = file_link.get_attribute("href")
                    file_path = file_link.text
                    
                    # Get code snippet
                    code_text = item.text
                    
                    # Search for API keys in this snippet
                    for pattern in self.API_KEY_PATTERNS:
                        matches = re.findall(pattern, code_text, re.IGNORECASE)
                        for match in matches:
                            key = match.strip("'\"")
                            if re.match(r'^AIza[0-9A-Za-z\-_]{35}$', key):
                                if key not in self.found_keys:
                                    self.found_keys.add(key)
                                    results.append((key, file_url, file_path, language))
                                    console.print(
                                        f"[bold green]Found key: {key[:20]}... "
                                        f"in {file_path}[/bold green]"
                                    )
                except NoSuchElementException:
                    continue
                    
        except Exception as e:
            if self.debug:
                console.print(f"[red]Error extracting results: {e}[/red]")
        
        return results

    def close(self):
        """Close the browser."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
