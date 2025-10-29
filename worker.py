import time
import threading
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import config

def get_used_coupons(base_filename):
    """Reads the log file for a given base filename and returns a set of used coupon codes."""
    used_coupons = set()
    log_file_path = os.path.join("coupon_logs", f"{base_filename}.txt")
    if not os.path.exists(log_file_path):
        return used_coupons
    
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                coupon_code = line.strip().split('#')[0].strip()
                if coupon_code:
                    used_coupons.add(coupon_code)
    except Exception as e:
        print(f"[ERROR] Could not read coupon log for {base_filename}: {e}")
        
    return used_coupons

def log_coupon_result(base_filename, coupon_code, result, log_func):
    """Appends the result of a coupon attempt to the log file and logs it."""
    log_message = f"Coupon '{coupon_code}': {result}"
    log_func(log_message)
    
    log_file_path = os.path.join("coupon_logs", f"{base_filename}.txt")
    try:
        with open(log_file_path, 'a', encoding='utf-8') as f:
            f.write(f"{coupon_code} # {result}\n")
    except Exception as e:
        # Use the logger to report this error
        log_func(f"Could not write to coupon log for {base_filename}: {e}", level=logging.ERROR)

import logging
from logging.handlers import RotatingFileHandler

def get_thread_safe_logger(base_filename, status_dict, lock):
    """
    Creates a logger that writes to a dedicated log file for the worker
    and also updates the status_dict with the latest log message for the UI.
    """
    # Create a unique logger for each worker thread. The name includes the UID to ensure uniqueness.
    logger_name = f"worker.{base_filename}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    # This is CRITICAL. It prevents the logger from passing its messages up to the root logger,
    # which would otherwise cause them to be duplicated in app.log.
    logger.propagate = False

    # Only add handlers if they haven't been added before. This prevents duplicate handlers
    # if this function were ever called multiple times for the same base_filename.
    if not logger.handlers:
        # Create a file handler that writes log messages to a file unique to this worker.
        log_file_path = os.path.join('logs', f"{base_filename}.log")
        
        # Use a rotating file handler to prevent log files from growing indefinitely.
        # 2MB max size, with 1 backup file.
        file_handler = RotatingFileHandler(log_file_path, maxBytes=1024 * 1024 * 2, backupCount=1, encoding='utf-8')
        
        # Define the format for the log messages.
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Add the configured file handler to the logger.
        logger.addHandler(file_handler)

    def log(message, level=logging.INFO):
        """
        Logs a message to the worker's dedicated log file and updates the UI status.
        """
        # Log the message using the configured logger.
        logger.log(level, message)
        
        # Update the in-memory dictionary for the UI preview. This must be thread-safe.
        with lock:
            status_dict['log_preview'] = message
            
    return log

def take_screenshot(driver, base_filename):
    """Saves a screenshot, overwriting the previous one for the same UID."""
    try:
        driver.save_screenshot(os.path.join("screenshots", f"{base_filename}.png"))
    except Exception as e:
        print(f"Could not take screenshot for {base_filename}: {e}")

def wait_and_find_element(driver, by, value, timeout=10, visible=True):
    """Waits for an element to be present/visible and returns it."""
    try:
        if visible:
            return WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((by, value))
            )
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    except TimeoutException:
        return None

def click_element(driver, by, value, log_func, description, timeout=10, retries=3):
    """Waits for an element to be clickable and clicks it."""
    for attempt in range(retries):
        try:
            element = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((by, value))
            )
            element.click()
            log_func(f"Clicked '{description}'.")
            return True
        except StaleElementReferenceException:
            log_func(f"Stale element ref for '{description}'. Retrying...", level=logging.WARNING)
            time.sleep(1)
        except Exception:
            # This can happen if another element is obscuring the button.
            # We'll try JS click as a fallback.
            log_func(f"Could not click '{description}', trying JS fallback.", level=logging.WARNING)
            return click_element_js(driver, by, value, log_func, description, timeout)
    log_func(f"ERROR: Failed to click '{description}' after {retries} retries.", level=logging.ERROR)
    return False

def click_element_js(driver, by, value, log_func, description, timeout=10):
    """Waits for an element and clicks it using JavaScript."""
    element = wait_and_find_element(driver, by, value, timeout, visible=False)
    if element:
        try:
            driver.execute_script("arguments[0].click();", element)
            log_func(f"Clicked '{description}' using JS.")
            return True
        except Exception as e:
            log_func(f"ERROR: JS click failed for '{description}'. Reason: {e}", level=logging.ERROR)
            return False
    log_func(f"ERROR: '{description}' not found for JS click.", level=logging.ERROR)
    return False

def redeem_coupons(driver, log_func, base_filename, coupons_to_try):
    """Iterates through coupons and attempts to redeem them."""
    if not coupons_to_try:
        log_func("No new coupons to try. Skipping.")
        return

    log_func(f"Starting redemption for {len(coupons_to_try)} new coupons.")
    for coupon in coupons_to_try:
        log_func(f"Processing coupon: {coupon}")
        take_screenshot(driver, base_filename)
        
        max_retries = 2
        result_logged = False
        for attempt in range(max_retries):
            log_func(f"Attempt {attempt + 1}/{max_retries} for {coupon}")

            # Try to clear any pop-ups before starting
            click_element_js(driver, By.XPATH, config.CANCEL_BUTTON, log_func, "Pre-emptive Cancel", timeout=3)
            
            coupon_input = wait_and_find_element(driver, By.XPATH, config.COUPON_CODE_INPUT)
            if not coupon_input:
                log_func("ERROR: Coupon input not found. Retrying...", level=logging.ERROR)
                driver.refresh()
                time.sleep(3)
                continue
            
            coupon_input.clear()
            coupon_input.send_keys(coupon)
            
            if not click_element(driver, By.XPATH, config.REDEEM_BUTTON_INITIAL, log_func, "Initial Redeem"):
                log_func(f"Failed to click initial redeem for {coupon}. Retrying.", level=logging.WARNING)
                continue

            # Check for immediate "Invalid Code" error
            error_element_pre = wait_and_find_element(driver, By.XPATH, config.ERROR_MESSAGE_P, timeout=2)
            if error_element_pre and "Data does not exist" in error_element_pre.text:
                error_text = error_element_pre.text.strip()
                log_coupon_result(base_filename, coupon, error_text, log_func)
                result_logged = True
                break 

            time.sleep(2) # Wait for confirmation dialog

            if not click_element_js(driver, By.XPATH, config.REDEEM_BUTTON_CONFIRM, log_func, "Confirm Redeem"):
                log_func(f"Failed to click confirm for {coupon}. Retrying.", level=logging.WARNING)
                continue

            # Check for success or other final messages
            if wait_and_find_element(driver, By.XPATH, config.SUCCESS_MESSAGE, timeout=3):
                log_coupon_result(base_filename, coupon, "Success", log_func)
                result_logged = True
                break 
            
            error_element_post = wait_and_find_element(driver, By.XPATH, config.ERROR_MESSAGE_P, timeout=3)
            if error_element_post:
                error_text = error_element_post.text.strip()
                log_coupon_result(base_filename, coupon, error_text, log_func)
                result_logged = True
                # Click cancel on "Already Used" to dismiss the dialog
                if "이미 사용" in error_text:
                    click_element_js(driver, By.XPATH, config.CANCEL_BUTTON, log_func, "Cancel on 'Already Used'", timeout=5)
                break
            else:
                log_func(f"WARNING: No known message for '{coupon}' on attempt {attempt + 1}.", level=logging.WARNING)
        
        if not result_logged:
            log_func(f"Failed to get a result for '{coupon}' after {max_retries} attempts.", level=logging.ERROR)
            log_coupon_result(base_filename, coupon, "Failed after multiple retries", log_func)
        
        time.sleep(2) # Pause between coupons

def process_uid(uid, comment, all_coupons, status_dict, lock, force_run=False):
    """
    Manages the browser automation lifecycle for a single UID and updates a shared status dict.
    """
    base_filename = f"{uid}_{comment}" if comment else uid
    log = get_thread_safe_logger(base_filename, status_dict, lock)
    
    with lock:
        status_dict['status'] = 'Preparing'
    
    used_coupons = get_used_coupons(base_filename)
    coupons_to_try = [c for c in all_coupons if c not in used_coupons]
    log(f"Found {len(used_coupons)} used coupons. Will try {len(coupons_to_try)} new coupons.")

    if not coupons_to_try and not force_run:
        log("No new coupons to try. Skipping session start as Force Run is not enabled.")
        with lock:
            status_dict['status'] = 'Finished'
        return

    driver = None
    try:
        with lock:
            status_dict['status'] = 'Starting Browser'
        
        chrome_options = Options()
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        # Add arguments for running in a container
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Remote(
            command_executor=config.SELENIUM_HUB_URL,
            options=chrome_options
        )
        # Store session ID for live view
        with lock:
            status_dict['session_id'] = driver.session_id

        driver.set_window_size(1920, 1080)
        driver.implicitly_wait(3)

        with lock:
            status_dict['status'] = 'Running'

        driver.get(config.BASE_URL)
        log(f"Navigated to {config.BASE_URL}")
        take_screenshot(driver, base_filename)

        # Banner can sometimes be slow to appear
        time.sleep(3)
        click_element(driver, By.XPATH, config.BANNER_CLOSE_BUTTON, log, "Banner close", timeout=5)
        take_screenshot(driver, base_filename)

        if not click_element(driver, By.XPATH, config.LOGIN_BUTTON, log, "Login button"):
            raise Exception("Failed to find or click Login button.")
        
        time.sleep(1)
        take_screenshot(driver, base_filename)

        uid_input = wait_and_find_element(driver, By.XPATH, config.UID_INPUT)
        if not uid_input:
            raise Exception("UID input field not found.")
        uid_input.send_keys(uid)
        
        if not click_element(driver, By.XPATH, config.UID_CHECK_BUTTON, log, "UID check button"):
            raise Exception("Failed to click UID check button.")
        
        # Attempt to click the confirm button up to 5 times with a 5-second interval.
        confirm_clicked = False
        for i in range(5):
            log(f"Attempt {i + 1}/5 to click confirm button.")
            if click_element(driver, By.XPATH, config.CONFIRM_BUTTON, log, "Confirm button"):
                confirm_clicked = True
                break  # Exit the loop if successful
            
            if i < 4: # Don't sleep after the final attempt
                log("Button not found or clickable, waiting 5 seconds to retry.")
                time.sleep(5)

        if not confirm_clicked:
            log("Could not click confirm button after 5 attempts. Continuing without confirmation.", level=logging.WARNING)

        log("Login successful. Waiting for page to load.")
        time.sleep(5)
        take_screenshot(driver, base_filename)

        # Click the 7 buttons before redeeming coupons
        log("Attempting to click 10 promotional buttons.")
        for i in range(1, 11):
            button_xpath = f'//*[@id="site-widget-1035124126946440"]/div[4]/div/div[3]/div[{i}]/div[5]/div[3]'
            if click_element(driver, By.XPATH, button_xpath, log, f"Promo Button {i}", timeout=5):
                time.sleep(1)
                x_button_xpath = '//*[@id="site-widget-1035124126946440"]/div[5]/div/div[2]/div/i'
                x_button = wait_and_find_element(driver, By.XPATH, x_button_xpath, timeout=2, visible=False)
                if x_button:
                    log("Found 'X' button, attempting to close pop-up.")
                    click_element_js(driver, By.XPATH, x_button_xpath, log, "'X' button", timeout=3)
                    time.sleep(1)
                else:
                    log(f"No 'X' button found after clicking Promo Button {i}.")
            else:
                log(f"Could not click Promo Button {i}, moving to the next.")
        
        log("Finished clicking promotional buttons.")
        take_screenshot(driver, base_filename)

        redeem_coupons(driver, log, base_filename, coupons_to_try)

        log("All tasks completed for this UID.")
        with lock:
            status_dict['status'] = 'Finished'

    except Exception as e:
        log(f"FATAL ERROR: {e}", level=logging.ERROR)
        with lock:
            status_dict['status'] = 'Error'
        # Take a final screenshot on error
        if driver:
            take_screenshot(driver, base_filename)
    finally:
        if driver:
            driver.quit()
            log("Browser session closed.")
