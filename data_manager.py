import os
import logging
from threading import Lock

# --- Constants ---
DATA_DIR = "data"
UIDS_FILE = os.path.join(DATA_DIR, "uids.txt")
COUPONS_FILE = os.path.join(DATA_DIR, "coupons.txt")

# --- Thread-safe lock for file operations ---
file_lock = Lock()

# --- Helper Functions ---

def ensure_data_dir_exists():
    """Ensures the data directory exists."""
    os.makedirs(DATA_DIR, exist_ok=True)

def read_file_lines(filepath):
    """Reads all lines from a file and returns them as a list."""
    try:
        with file_lock:
            with open(filepath, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        return []

def write_file_lines(filepath, lines):
    """Writes a list of lines to a file, overwriting it."""
    try:
        with file_lock:
            with open(filepath, 'w', encoding='utf-8') as f:
                for line in lines:
                    f.write(f"{line}\n")
        return True
    except Exception as e:
        logging.error(f"Error writing to file {filepath}: {e}")
        return False

# --- UID Management ---

def get_uids_list():
    """
    Reads the uids.txt file and returns a list of dictionaries.
    Each dictionary contains 'uid', 'comment', and 'id'.
    """
    lines = read_file_lines(UIDS_FILE)
    uids_list = []
    for line in lines:
        if '#' in line:
            parts = line.split('#', 1)
            uid, comment = parts[0].strip(), parts[1].strip()
            uids_list.append({'uid': uid, 'comment': comment, 'id': f"{uid}_{comment}"})
    return uids_list

def get_uids_raw():
    """Returns the raw content of the uids.txt file."""
    try:
        with file_lock:
            with open(UIDS_FILE, 'r', encoding='utf-8') as f:
                return f.read()
    except FileNotFoundError:
        return ""

def save_uids_raw(content):
    """Saves raw text content to the uids.txt file."""
    try:
        with file_lock:
            with open(UIDS_FILE, 'w', encoding='utf-8') as f:
                f.write(content)
        return True
    except Exception as e:
        logging.error(f"Error saving UIDs file: {e}")
        return False

def add_uid(uid, comment):
    """Adds a new UID and comment to the uids.txt file."""
    lines = read_file_lines(UIDS_FILE)
    new_line = f"{uid} #{comment}"
    if new_line not in lines:
        lines.append(new_line)
        return write_file_lines(UIDS_FILE, lines)
    return True # Already exists

def delete_uid(uid_to_delete):
    """Deletes a UID from the uids.txt file."""
    lines = read_file_lines(UIDS_FILE)
    original_count = len(lines)
    lines = [line for line in lines if not line.strip().startswith(uid_to_delete)]
    
    if len(lines) < original_count:
        return write_file_lines(UIDS_FILE, lines)
    return False # Not found

# --- Coupon Management ---

def get_all_coupons():
    """Reads coupons from coupons.txt."""
    return read_file_lines(COUPONS_FILE)

def get_coupons_raw():
    """Returns the raw content of the coupons.txt file."""
    try:
        with file_lock:
            with open(COUPONS_FILE, 'r', encoding='utf-8') as f:
                return f.read()
    except FileNotFoundError:
        return ""

def save_coupons_raw(content):
    """Saves raw text content to the coupons.txt file."""
    try:
        with file_lock:
            with open(COUPONS_FILE, 'w', encoding='utf-8') as f:
                f.write(content)
        return True
    except Exception as e:
        logging.error(f"Error saving coupons file: {e}")
        return False

def add_coupon(coupon_code):
    """Adds a new coupon to the coupons.txt file."""
    coupons = get_all_coupons()
    if coupon_code not in coupons:
        coupons.append(coupon_code)
        return write_file_lines(COUPONS_FILE, coupons)
    return True # Already exists

def delete_coupon(coupon_to_delete):
    """Deletes a coupon from the coupons.txt file."""
    coupons = get_all_coupons()
    if coupon_to_delete in coupons:
        coupons.remove(coupon_to_delete)
        return write_file_lines(COUPONS_FILE, coupons)
    return False # Not found

# --- Initialization ---
ensure_data_dir_exists()
