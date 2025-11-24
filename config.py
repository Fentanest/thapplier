
import os

# -- Selenium Hub Configuration ---
# It reads from the "SELENIUM_HUB_URL" environment variable.
# If the variable is not set, it defaults to "http://localhost:4444".
SELENIUM_HUB_URL = os.getenv("SELENIUM_HUB_URL", "http://localhost:4444")

# --- Concurrency Settings ---
# The maximum number of concurrent Chrome browsers to run.
# It reads from the "MAX_CONCURRENT_SESSIONS" environment variable.
# If the variable is not set, it defaults to 1.
MAX_CONCURRENT_SESSIONS = int(os.getenv("MAX_CONCURRENT_SESSIONS", 1))

# --- Delay Settings ---
# The delay in seconds between starting each Selenium session.
# It reads from the "DELAY_BETWEEN_SESSIONS" environment variable.
# If the variable is not set, it defaults to 10.
DELAY_BETWEEN_SESSIONS = int(os.getenv("DELAY_BETWEEN_SESSIONS", 10))

# --- User Data ---
# IMPORTANT: UIDs and Coupon Codes are now loaded from uids.txt and coupons.txt respectively.

# --- Authentication Settings ---
# Credentials for basic HTTP authentication.
# It reads from "AUTH_USERNAME" and "AUTH_PASSWORD" environment variables.
# If the variables are not set, it uses default values.
AUTH_USERNAME = os.getenv("AUTH_USERNAME", "topheroes")
AUTH_PASSWORD = os.getenv("AUTH_PASSWORD", "applier")

# --- Telegram Bot Configuration ---
# It reads from "TELEGRAM_BOT_TOKEN" and "TELEGRAM_CHAT_ID" environment variables.
# If the variables are not set, the bot functionality will be disabled.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


# --- Website and XPath Locators ---
# It reads from the "BASE_URL" environment variable.
BASE_URL = os.getenv("BASE_URL", "https://topheroes.store.kopglobal.com/ko/")

# --- Main Page Locators ---
BANNER_CLOSE_BUTTON = '//*[@id="__layout"]//i[@class="el-icon-close"]'
LOGIN_BUTTON = '//*[@id="site-widget-2121094971520928"]//span[text()="로그인"]'

# --- Login Modal Locators ---
UID_INPUT = '//*[@id="__layout"]//input[@placeholder="UID를 입력해 주세요"]'
UID_CHECK_BUTTON = '//*[@id="__layout"]//i[@class="el-icon-check"]'
CONFIRM_BUTTON = '//*[@id="__layout"]//button[normalize-space(text())="확인"]'

# --- Coupon Redemption Locators ---
COUPON_CODE_INPUT = '//*[@id="site-widget-1885701553012187"]//input[@placeholder="선물 코드 입력"]'
REDEEM_BUTTON_INITIAL = '//*[@id="site-widget-1885701553012187"]//button[contains(@class, "site-button") and normalize-space(text())="교환하기"]'
REDEEM_BUTTON_CONFIRM = "//div[contains(@class, 'dialog-actions')]//button[contains(@class, 'confirm')]"
CANCEL_BUTTON = "//div[contains(@class, 'dialog-actions')]//button[contains(@class, 'cancel')]"

# --- Feedback Message Locators ---
# These messages appear dynamically after attempting to redeem a coupon.
ERROR_MESSAGE_P = '//*[@id="im-app"]//div[contains(@class, "el-message--error") and @role="alert"]'
SUCCESS_MESSAGE = '//*[@id="im-app"]//p[@class="el-message__content" and text()="Success"]'
