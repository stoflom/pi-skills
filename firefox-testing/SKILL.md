---
name: firefox-testing
description: Provides capabilities for automated web testing using Firefox and the Marionette protocol via Selenium and GeckoDriver.
---

# Firefox Marionette Testing Skill

This skill provides capabilities for automated web testing using Firefox and the Marionette protocol via Selenium and GeckoDriver.


## Capabilities

- **Automated Browser Management**: Automatically handles `geckodriver` installation and manages Firefox lifecycle (start/stop).
- **Headless Mode**: Default behavior is headless, suitable for agent environments.
- **Navigation**: `navigate(url)`, `go_back()`, `go_forward()`, `refresh()`
- **Viewport Management**: `set_window_size(width, height)`, `get_window_size()`, `set_window_position(x, y)`, `maximize_window()`, `fullscreen_window()`
- **Element Queries**: `find_element(by, value)`, `find_elements(by, value)`, `get_text()`, `get_html()`, `get_element_attribute()`, `get_element_property()`, `get_computed_style()`, `get_element_rect()`, `is_element_present()`, `is_element_visible()`
- **Element Interaction**: `click()`, `double_click()`, `right_click()`, `hover()`, `drag_and_drop()`, `type_text()`, `append_text()`, `send_keys()`, `select_dropdown_option()`
- **Scrolling**: `scroll_to(by, value)`, `scroll_by(x, y)`, `scroll_to_top()`, `scroll_to_bottom()`
- **Screenshot**: `screenshot(filename)`, `screenshot_element(by, value, filename)`
- **JavaScript**: `execute_script(script, *args)`, `execute_async_script(script, *args)`
- **Cookies**: `get_all_cookies()`, `add_cookie()`, `delete_all_cookies()`
- **Wait Utilities**: `wait_for_element()`, `wait_for_text()`, `wait_for_url_contains()`, `wait_for_not_present()`, `wait(seconds)`

## How to Use

To use this skill, import the `FirefoxTester` class from the local skill directory.

### Example Usage in a Python script

```python
import sys
import os

# Add the skill directory to sys.path to allow importing
skill_path = "/home/stoflom/.pi/agent/skills/firefox-testing"
if skill_path not in sys.path:
    sys.path.append(skill_path)

from firefox_tester import FirefoxTester
from selenium.webdriver.common.by import By

def run_test():
    with FirefoxTester(headless=True) as tester:
        # 1. Navigate to a site
        tester.navigate("https://example.com")
        
        # 2. Check title
        title = tester.get_title()
        print(f"Page title is: {title}")
        assert "Example Domain" in title
        
        # 3. Take a screenshot
        tester.screenshot("example_domain.png")
        
        # 4. Find and interact with elements (if any)
        # ...
        
        print("Test completed successfully!")

if __name__ == "__main__":
    run_test()
```

## Troubleshooting

- **Geckodriver issues**: The skill uses `webdriver-manager` to handle geckodriver. Ensure internet access is available for the first run.
- **Headless environment**: If running in a non-headless environment, change `headless=False` in `FirefoxTester`.
- **Firefox version**: If Firefox is not in the PATH, you may need to specify the binary location in `FirefoxTester`.
