import os
import time
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager

class FirefoxTester:
    """
    A wrapper around Selenium WebDriver for Firefox to simplify testing tasks.

    Capabilities:
        - Automated browser management (start/stop, headless mode)
        - Navigation (go back/forward/refresh)
        - Element interaction (click, type, send keys, hover, drag-and-drop)
        - Element queries (find by locator, get text, get attributes, check visibility)
        - Viewport management (resize, position, scroll, fullscreen)
        - Screenshot capture (full page or individual element)
        - JavaScript execution (sync and async)
        - Wait utilities (explicit waits, polling)
        - Cookie management
        - CSS style inspection
    """

    def __init__(self, headless=True, window_size=None):
        self.headless = headless
        self.driver = None
        self.window_size = window_size  # (width, height) or None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        print("Starting Firefox via GeckoDriver...")
        options = Options()
        if self.headless:
            options.add_argument("--headless")

        try:
            service = Service(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=options)
            if self.window_size:
                self.set_window_size(*self.window_size)
            print("Firefox started successfully.")
        except Exception as e:
            print(f"Failed to start Firefox: {e}")
            raise

    def stop(self):
        if self.driver:
            print("Closing Firefox...")
            self.driver.quit()
            self.driver = None

    # ── Navigation ─────────────────────────────────────────────────

    def navigate(self, url):
        """Navigate to a URL."""
        print(f"Navigating to: {url}")
        self.driver.get(url)

    def go_back(self):
        """Go back in browser history."""
        print("Going back...")
        self.driver.back()

    def go_forward(self):
        """Go forward in browser history."""
        print("Going forward...")
        self.driver.forward()

    def refresh(self):
        """Refresh the current page."""
        print("Refreshing page...")
        self.driver.refresh()

    # ── Page info ──────────────────────────────────────────────────

    def get_title(self):
        return self.driver.title

    def get_url(self):
        return self.driver.current_url

    def get_page_source(self):
        return self.driver.page_source

    # ── Viewport management ────────────────────────────────────────

    def set_window_size(self, width, height):
        """Resize the browser window to the specified width and height."""
        print(f"Setting window size to: {width}x{height}")
        self.driver.set_window_size(width, height)

    def get_window_size(self):
        """Get the current browser window size."""
        return self.driver.get_window_size()

    def set_window_position(self, x, y):
        """Position the browser window at the specified coordinates."""
        print(f"Setting window position to: ({x}, {y})")
        self.driver.set_window_position(x, y)

    def get_window_position(self):
        """Get the current browser window position."""
        return self.driver.get_window_position()

    def maximize_window(self):
        """Maximize the browser window."""
        print("Maximizing window...")
        self.driver.maximize_window()

    def fullscreen_window(self):
        """Toggle fullscreen mode."""
        print("Toggling fullscreen...")
        self.driver.fullscreen_window()

    # ── Element queries ────────────────────────────────────────────

    def find_element(self, by, value, timeout=10):
        """Find a single element by locator, waiting for presence."""
        print(f"Finding element: {by}={value}")
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.presence_of_element_located((by, value)))

    def find_elements(self, by, value, timeout=10):
        """Find all elements matching the locator, waiting for visibility."""
        print(f"Finding elements: {by}={value}")
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.visibility_of_all_elements_located((by, value)))

    def is_element_present(self, by, value, timeout=5):
        """Check if an element is present on the page."""
        try:
            self.find_element(by, value, timeout)
            return True
        except Exception:
            return False

    def is_element_visible(self, by, value, timeout=5):
        """Check if an element is visible on the page."""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
            return True
        except Exception:
            return False

    def get_element_rect(self, by, value, timeout=10):
        """Get element position/size: {x, y, width, height}."""
        el = self.find_element(by, value, timeout)
        return el.rect

    def get_element_property(self, by, value, prop, timeout=10):
        """Get a JS property from an element."""
        el = self.find_element(by, value, timeout)
        return el.get_property(prop)

    def get_element_attribute(self, by, value, attr, timeout=10):
        """Get an HTML attribute from an element."""
        el = self.find_element(by, value, timeout)
        return el.get_attribute(attr)

    def get_computed_style(self, by, value, prop, timeout=10):
        """Get the computed CSS style value for an element."""
        el = self.find_element(by, value, timeout)
        return self.execute_script(
            "const el = arguments[0]; return window.getComputedStyle(el).getPropertyValue(arguments[1]);",
            el, prop
        )

    def get_text(self, by, value, timeout=10):
        """Get the visible text content from an element."""
        element = self.find_element(by, value, timeout)
        return element.text

    def get_html(self, by, value, timeout=10):
        """Get the innerHTML of an element."""
        element = self.find_element(by, value, timeout)
        return element.get_attribute("innerHTML")

    # ── Element interaction ────────────────────────────────────────

    def click(self, by, value, timeout=10):
        """Click an element."""
        element = self.find_element(by, value, timeout)
        element.click()

    def double_click(self, by, value, timeout=10):
        """Double-click an element."""
        from selenium.webdriver.common.action_chains import ActionChains
        el = self.find_element(by, value, timeout)
        ActionChains(self.driver).double_click(el).perform()

    def right_click(self, by, value, timeout=10):
        """Right-click (context-click) an element."""
        from selenium.webdriver.common.action_chains import ActionChains
        el = self.find_element(by, value, timeout)
        ActionChains(self.driver).context_click(el).perform()

    def drag_and_drop(self, source_by, source_value, target_by, target_value, timeout=10):
        """Drag and drop one element onto another."""
        from selenium.webdriver.common.action_chains import ActionChains
        source = self.find_element(source_by, source_value, timeout)
        target = self.find_element(target_by, target_value, timeout)
        ActionChains(self.driver).drag_and_drop(source, target).perform()

    def type_text(self, by, value, text, timeout=10):
        """Type text into an element (clears first)."""
        element = self.find_element(by, value, timeout)
        element.clear()
        element.send_keys(text)

    def append_text(self, by, value, text, timeout=10):
        """Append text to an element (does not clear)."""
        element = self.find_element(by, value, timeout)
        element.send_keys(text)

    def send_keys(self, by, value, keys, timeout=10):
        """Send special keys (e.g., Keys.ENTER) to an element."""
        element = self.find_element(by, value, timeout)
        element.send_keys(keys)

    def select_dropdown_option(self, by, value, option_text_or_index, timeout=10):
        """Select an option from a <select> dropdown by text, index, or value."""
        from selenium.webdriver.support.ui import Select
        element = self.find_element(by, value, timeout)
        select = Select(element)
        if isinstance(option_text_or_index, int):
            select.select_by_index(option_text_or_index)
        elif str(option_text_or_index).startswith("value="):
            select.select_by_value(str(option_text_or_index)[6:])
        else:
            select.select_by_visible_text(option_text_or_index)

    def hover(self, by, value, timeout=10):
        """Hover over an element."""
        from selenium.webdriver.common.action_chains import ActionChains
        el = self.find_element(by, value, timeout)
        ActionChains(self.driver).move_to_element(el).perform()

    # ── Scrolling ──────────────────────────────────────────────────

    def scroll_to(self, by, value, timeout=10):
        """Scroll an element into view."""
        el = self.find_element(by, value, timeout)
        self.execute_script(
            "arguments[0].scrollIntoView({block: 'center', inline: 'center'});", el
        )
        time.sleep(0.1)

    def scroll_to_element(self, el):
        """Scroll a WebElement into view."""
        self.execute_script(
            "arguments[0].scrollIntoView({block: 'center', inline: 'center'});", el
        )
        time.sleep(0.1)

    def scroll_by(self, x, y):
        """Scroll the page by the specified pixel amounts."""
        self.execute_script(f"window.scrollBy({x}, {y});")
        time.sleep(0.1)

    def scroll_to_top(self):
        """Scroll to the top of the page."""
        self.execute_script("window.scrollTo(0, 0);")
        time.sleep(0.1)

    def scroll_to_bottom(self):
        """Scroll to the bottom of the page."""
        self.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.1)

    # ── Screenshot ─────────────────────────────────────────────────

    def screenshot(self, filename):
        """Take a full-page screenshot."""
        print(f"Taking screenshot: {filename}")
        self.driver.save_screenshot(filename)

    def screenshot_element(self, by, value, filename, timeout=10):
        """Take a screenshot of a specific element only."""
        el = self.find_element(by, value, timeout)
        el.screenshot(filename)

    # ── JavaScript execution ───────────────────────────────────────

    def execute_script(self, script, *args):
        """Execute synchronous JavaScript in the browser context."""
        return self.driver.execute_script(script, *args)

    def execute_async_script(self, script, *args):
        """Execute asynchronous JavaScript in the browser context."""
        return self.driver.execute_async_script(script, *args)

    # ── Cookies ────────────────────────────────────────────────────

    def get_all_cookies(self):
        """Get all cookies."""
        return self.driver.get_cookies()

    def add_cookie(self, cookie_dict):
        """Add a cookie."""
        self.driver.add_cookie(cookie_dict)

    def delete_all_cookies(self):
        """Delete all cookies."""
        self.driver.delete_all_cookies()

    # ── Wait utilities ─────────────────────────────────────────────

    def wait_for_element(self, by, value, condition=EC.presence_of_element_located, timeout=10):
        """
        Wait for an element to meet a condition.
        Common conditions:
            EC.presence_of_element_located  - element exists in DOM
            EC.visibility_of_element_located - element is visible
            EC.element_to_be_clickable     - element is clickable
            EC.element_located_to_be_selected - element is selected
        """
        print(f"Waiting for {by}={value}...")
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(condition((by, value)))

    def wait_for_text(self, by, value, text, timeout=10):
        """Wait for an element to contain specific text."""
        print(f"Waiting for {by}={value} to contain text: {text}")
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.text_to_be_present_in_element((by, value), text))

    def wait_for_url_contains(self, substring, timeout=10):
        """Wait for URL to contain a substring."""
        print(f"Waiting for URL to contain: {substring}")
        wait = WebDriverWait(self.driver, timeout)
        return wait.until(EC.url_contains(substring))

    def wait_for_not_present(self, by, value, timeout=10):
        """Wait for an element to be removed from the DOM."""
        print(f"Waiting for {by}={value} to disappear...")
        wait = WebDriverWait(self.driver, timeout)
        return wait.until_not(EC.presence_of_element_located((by, value)))

    def wait(self, seconds):
        """Simple sleep/poll (no-op wait)."""
        print(f"Waiting {seconds} seconds...")
        time.sleep(seconds)

    # ── Low-level access ───────────────────────────────────────────

    @property
    def driver(self):
        return self._driver

    @driver.setter
    def driver(self, value):
        self._driver = value


if __name__ == "__main__":
    # Simple self-test
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        with FirefoxTester() as tester:
            tester.navigate("https://www.google.com")
            print(f"Test Title: {tester.get_title()}")
            if "Google" in tester.get_title():
                print("Self-test passed!")
            else:
                print("Self-test failed!")
