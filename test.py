from seleniumbase import SB
from selenium.webdriver.chrome.options import Options

with SB(uc=True, test=True, locale="tw") as sb:
    # Set up the Chrome options
    chrome_options = Options()
    #chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Create a new instance of the Chrome driver with the options
    sb.open("https://www.example.com")
    sb.uc_gui_click_captcha()
    while True:
        pass