
import threading
import time
import os

# Import configuration and the worker function
import config
from worker import process_uid

def load_uids_from_file(filepath="uids.txt"):
    """
    Loads UIDs and their comments from a text file.
    Returns a list of tuples (uid, comment).
    """
    uids_with_comments = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                parts = line.split('#', 1)
                uid = parts[0].strip()
                # Take the comment part, replace spaces for cleaner filenames, or set to None
                comment = parts[1].strip().replace(' ', '_') if len(parts) > 1 else None
                
                if uid:
                    uids_with_comments.append((uid, comment))
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found.")
    return uids_with_comments

def load_coupons_from_file(filepath="coupons.txt"):
    """
    Loads coupon codes from a text file, ignoring empty lines.
    """
    coupons = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                coupon = line.strip()
                if coupon:
                    coupons.append(coupon)
    except FileNotFoundError:
        print(f"Error: The file '{filepath}' was not found.")
    return coupons

def main():
    """
    Main entry point for the automation script.
    Manages concurrent execution of browser tasks using a thread pool.
    """
    # Create directories for logs if they don't exist
    os.makedirs("logs", exist_ok=True)
    os.makedirs("coupon_logs", exist_ok=True)

    # Load UIDs and Coupon Codes from files
    uids_with_comments = load_uids_from_file()
    coupons = load_coupons_from_file()

    if not uids_with_comments or not coupons:
        print("UIDs or Coupons not found. Please check uids.txt and coupons.txt.")
        return

    start_time = time.time()
    print("--- Starting Top Heroes Coupon Redeemer ---")
    print(f"Found {len(uids_with_comments)} UIDs to process.")
    print(f"Found {len(coupons)} coupon codes to try for each UID.")
    print(f"Max concurrent sessions: {config.MAX_CONCURRENT_SESSIONS}")
    print("-" * 40)

    # A semaphore is used to limit the number of concurrent browser sessions.
    # This prevents overwhelming the Selenium Hub or the target website.
    semaphore = threading.Semaphore(config.MAX_CONCURRENT_SESSIONS)
    
    threads = []
    for uid, comment in uids_with_comments:
        # For each UID, a new thread is created.
        # The `process_uid` function from worker.py is the target.
        # The uid, comment, full coupon list, and semaphore are passed to the worker.
        thread = threading.Thread(target=process_uid, args=(uid, comment, coupons, semaphore))
        threads.append(thread)
        thread.start()
        time.sleep(0.1) # Stagger thread starts slightly

    # Wait for all threads to complete their execution.
    # The `join()` method blocks the main thread until the worker thread finishes.
    for thread in threads:
        thread.join()

    end_time = time.time()
    print("-" * 40)
    print("All UIDs have been processed.")
    print(f"Total execution time: {end_time - start_time:.2f} seconds.")
    print("--- Script Finished ---")

if __name__ == "__main__":
    # It's good practice to ensure the script is being run directly.
    main()
