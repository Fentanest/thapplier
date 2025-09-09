from flask import Flask, render_template, request, jsonify, Response, send_from_directory, url_for
from functools import wraps
import os
import threading
import time
import subprocess
import shutil
from datetime import datetime, timedelta

# Import project modules
import worker
import config
import data_manager # Use the new data manager

import logging
from logging.handlers import RotatingFileHandler

# --- Logging Setup ---
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] - %(message)s')

# File Handler
log_file = os.path.join('logs', 'app.log')
file_handler = RotatingFileHandler(log_file, maxBytes=1024 * 1024 * 5, backupCount=2) # 5MB per file, 2 backups
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.INFO)

# Get root logger and add handlers
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# Get Gunicorn's logger and redirect its output to our handlers
gunicorn_logger = logging.getLogger('gunicorn.error')
gunicorn_logger.handlers = root_logger.handlers
gunicorn_logger.setLevel(logging.INFO)

app = Flask(__name__)
# Integrate Flask's logger with our handlers
app.logger.handlers = root_logger.handlers
app.logger.setLevel(logging.INFO)

# --- Authentication ---
def check_auth(username, password):
    """This function is called to check if a username /
    password combination is valid.
    """
    return username == config.AUTH_USERNAME and password == config.AUTH_PASSWORD

def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated

# Thread-safe in-memory store for running threads and their status

thread_lock = threading.Lock()
# { "base_filename": {"thread": obj, "status": str, "log_preview": str, "display_name": str, "session_id": str} }
running_threads = {}
# Use a semaphore to limit concurrent browser sessions
session_semaphore = threading.Semaphore(config.MAX_CONCURRENT_SESSIONS)

# Ensure necessary directories exist
os.makedirs("logs", exist_ok=True)
os.makedirs("coupon_logs", exist_ok=True)
os.makedirs("screenshots", exist_ok=True)
data_manager.ensure_data_dir_exists()

def get_uids_map():
    """Reads data/uids.txt and returns a map of base_filename to uid/comment."""
    uids_list = data_manager.get_uids_list()
    uids_map = {}
    for item in uids_list:
        base_filename = f"{item['uid']}_{item['comment']}"
        uids_map[base_filename] = {'uid': item['uid'], 'comment': item['comment']}
    return uids_map

def worker_wrapper(uid, comment, all_coupons, base_filename, force_run=False):
    """Wrapper to manage semaphore and status dict for the worker thread."""
    with session_semaphore:
        # The worker will update its own status in the running_threads dict
        worker.process_uid(uid, comment, all_coupons, running_threads[base_filename], thread_lock, force_run=force_run)

def perform_backup():
    """Backs up the uids.txt and coupons.txt files."""
    data_dir = 'data'
    files_to_backup = ['uids.txt', 'coupons.txt']
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    
    for filename in files_to_backup:
        source_path = os.path.join(data_dir, filename)
        if os.path.exists(source_path):
            try:
                # e.g., uids_2025-08-02_000000.txt
                backup_filename = f"{os.path.splitext(filename)[0]}_{timestamp}.txt"
                dest_path = os.path.join(data_dir, backup_filename)
                shutil.copy2(source_path, dest_path)
                app.logger.info(f"Successfully backed up {source_path} to {dest_path}")
            except Exception as e:
                app.logger.error(f"Error backing up {source_path}: {e}")


def dispatch_workers(selected_ids, selected_coupons, force_run=False):
    """
    Iterates through selected UIDs and starts a worker thread for each,
    with a delay between each start. This runs in a background thread
    and does not block the main Flask app.
    """
    uids_map = get_uids_map()
    
    for i, base_filename in enumerate(selected_ids):
        # For any thread after the first one, wait for the configured delay.
        if i > 0:
            app.logger.info(f"Waiting {config.DELAY_BETWEEN_SESSIONS} seconds before starting next session...")
            time.sleep(config.DELAY_BETWEEN_SESSIONS)

        with thread_lock:
            # Double-check that the thread hasn't been started by another request or is finished
            if base_filename in uids_map and (base_filename not in running_threads or not running_threads[base_filename]['thread'].is_alive()):
                uid_info = uids_map[base_filename]
                
                app.logger.info(f"Preparing to start worker for: {base_filename}")

                # Initialize status dict for the new thread
                running_threads[base_filename] = {
                    'status': 'Queued',
                    'log_preview': 'Waiting for an available session...', 
                    'display_name': f"{uid_info['uid']} ({uid_info['comment']})",
                    'session_id': None
                }
                
                thread = threading.Thread(
                    target=worker_wrapper,
                    args=(uid_info['uid'], uid_info['comment'], selected_coupons, base_filename, force_run)
                )
                thread.daemon = True
                thread.start()
                running_threads[base_filename]['thread'] = thread
                app.logger.info(f"Successfully started worker thread for {base_filename}")
            else:
                app.logger.warning(f"Skipping already running or invalid worker: {base_filename}")


@app.route('/run', methods=['POST'])
@requires_auth
def run_automation():
    """
    Receives a request to start automation and kicks off the dispatcher
    thread to manage the process in the background.
    """
    data = request.json
    selected_ids = data.get('uids', [])
    selected_coupons = data.get('coupons', [])

    # Ensure selected_ids is always a list
    if isinstance(selected_ids, str):
        selected_ids = [selected_ids]
    
    if not selected_ids:
        return jsonify({'status': 'error', 'message': 'No UIDs selected.'}), 400
    
    if not selected_coupons:
        return jsonify({'status': 'error', 'message': 'No coupons selected.'}), 400

    # Start the dispatcher thread to handle the staggered start
    dispatcher = threading.Thread(
        target=dispatch_workers,
        args=(selected_ids, selected_coupons, False) # Pass force_run=False
    )
    dispatcher.daemon = True
    dispatcher.start()

    return jsonify({
        'status': 'success',
        'message': f'Automation process initiated for {len(selected_ids)} UIDs. They will start sequentially.'
    })

@app.route('/force_run', methods=['POST'])
@requires_auth
def force_run_automation():
    """
    Receives a request to FORCE start automation and kicks off the dispatcher
    thread to manage the process in the background.
    """
    data = request.json
    selected_ids = data.get('uids', [])
    selected_coupons = data.get('coupons', [])

    # Ensure selected_ids is always a list
    if isinstance(selected_ids, str):
        selected_ids = [selected_ids]
    
    if not selected_ids:
        return jsonify({'status': 'error', 'message': 'No UIDs selected.'}), 400
    
    # For force run, coupons are not strictly required to start a session
    # but we still need to pass the list, even if empty.

    # Start the dispatcher thread to handle the staggered start
    dispatcher = threading.Thread(
        target=dispatch_workers,
        args=(selected_ids, selected_coupons, True) # Pass force_run=True
    )
    dispatcher.daemon = True
    dispatcher.start()

    return jsonify({
        'status': 'success',
        'message': f'Force run process initiated for {len(selected_ids)} UIDs. They will start sequentially.'
    })

def backup_scheduler():
    """Runs a loop to schedule backups at midnight every day."""
    app.logger.info("Backup scheduler started.")
    while True:
        now = datetime.now()
        # Calculate the next midnight
        tomorrow = now.date() + timedelta(days=1)
        midnight = datetime.combine(tomorrow, datetime.min.time())
        
        sleep_seconds = (midnight - now).total_seconds()
        
        app.logger.info(f"Scheduler will sleep for {sleep_seconds / 3600:.2f} hours until next backup.")
        time.sleep(sleep_seconds)
        
        # Time to wake up and do the backup
        app.logger.info("Performing scheduled daily backup...")
        perform_backup()
        # Sleep for a short while to ensure we don't run it twice in the same second
        time.sleep(1)


@app.context_processor
def inject_global_vars():
    """Injects global variables into all templates."""
    # Provide the raw hub URL to the template
    selenium_hub_ui = config.SELENIUM_HUB_URL
    return {
        'selenium_hub_url': selenium_hub_ui
    }

@app.route('/logout')
def logout():
    """Logs the user out by sending a 401 response."""
    return authenticate()

@app.route('/')
@requires_auth
def index():
    """Renders the main control panel page."""
    uids_list = data_manager.get_uids_list()
    uids_raw = data_manager.get_uids_raw()
    coupons_list = data_manager.get_all_coupons()
    coupons_raw = data_manager.get_coupons_raw()

    return render_template('index.html', 
                           uids_list=uids_list, 
                           uids_raw=uids_raw, 
                           coupons_list=coupons_list,
                           coupons_raw=coupons_raw)

@app.route('/monitoring')
@requires_auth
def monitoring():
    """Renders the monitoring page."""
    return render_template('monitoring.html')

@app.route('/full-logs')
@requires_auth
def full_logs_page():
    """Renders the real-time log viewer page."""
    return render_template('logs.html')

@app.route('/stream-all-logs')
@requires_auth
def stream_all_logs():
    """Streams the content of app.log file."""
    def generate():
        log_file_path = os.path.join('logs', 'app.log')
        if not os.path.exists(log_file_path):
            # Try to create the file if it doesn't exist, as the app might be idle.
            try:
                with open(log_file_path, 'a'):
                    os.utime(log_file_path, None)
                app.logger.info("app.log was not found, so it was created.")
            except Exception as e:
                app.logger.error(f"Could not create app.log: {e}")
                yield "data: Log file could not be created.\n\n"
                return

        with open(log_file_path, 'r', encoding='utf-8') as log_file:
            # Seek to the end of the file
            log_file.seek(0, 2)
            
            while True:
                line = log_file.readline()
                if not line:
                    time.sleep(0.1)  # Wait for new lines
                    continue
                yield f"data: {line.strip()}\n\n"

    return Response(generate(), mimetype='text/event-stream')

@app.route('/logs')
@requires_auth
def logs_page():
    """Renders the main log viewer page."""
    return render_template('old_logs.html')

@app.route('/api/logs')
@requires_auth
def api_get_logs():
    """API endpoint to get a list of all log files."""
    log_files = []
    coupon_log_files = []

    # Scan logs directory
    if os.path.exists('logs'):
        for filename in sorted(os.listdir('logs'), reverse=True):
            if filename.endswith('.log'):
                log_files.append(filename)
    
    # Scan coupon_logs directory
    if os.path.exists('coupon_logs'):
        for filename in sorted(os.listdir('coupon_logs'), reverse=True):
            if filename.endswith('.txt'):
                coupon_log_files.append(filename)
            
    return jsonify({
        'logs': log_files,
        'coupon_logs': coupon_log_files
    })

@app.route('/api/log-content')
@requires_auth
def api_get_log_content():
    """API endpoint to get the content of a specific log file."""
    log_type = request.args.get('type')
    filename = request.args.get('file')

    if not log_type or not filename:
        return jsonify({'error': 'Missing log type or filename'}), 400

    if log_type == 'log':
        dir_path = 'logs'
    elif log_type == 'coupon':
        dir_path = 'coupon_logs'
    else:
        return jsonify({'error': 'Invalid log type'}), 400

    file_path = os.path.join(dir_path, filename)
    
    # Security check to prevent directory traversal
    if not os.path.abspath(file_path).startswith(os.path.abspath(dir_path)):
        return jsonify({'error': 'Invalid file path'}), 400

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        content = "File not found or empty."
        
    return jsonify({'filename': filename, 'content': content})




@app.route('/status')
@requires_auth
def get_status():
    """Returns the status of all running and finished threads."""
    with thread_lock:
        # Clean up finished threads that are no longer active
        active_threads = {}
        for key, data in running_threads.items():
            if 'thread' in data and data['thread'].is_alive():
                active_threads[key] = data
            elif data.get('status') not in ['Finished', 'Error']:
                # If thread is dead but status wasn't final, mark as Finished
                data['status'] = 'Finished'
                active_threads[key] = data
            else: # Already Finished or Error
                 active_threads[key] = data


        running_threads.clear()
        running_threads.update(active_threads);

        # Create a JSON-serializable copy of the status dictionary
        status_copy = {}
        for key, value in running_threads.items():
            status_copy[key] = {
                'status': value.get('status', 'Unknown'),
                'log_preview': value.get('log_preview', ''),
                'display_name': value.get('display_name', key),
                'session_id': value.get('session_id')
            }
        
        return jsonify(status_copy)

@app.route('/save/uids', methods=['POST'])
@requires_auth
def save_uids():
    content = request.json.get('content', '')
    if data_manager.save_uids_raw(content):
        return jsonify({'status': 'success', 'message': 'UIDs file saved successfully.'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to save UIDs file.'}), 500

@app.route('/save/coupons', methods=['POST'])
@requires_auth
def save_coupons():
    content = request.json.get('content', '')
    if data_manager.save_coupons_raw(content):
        return jsonify({'status': 'success', 'message': 'Coupons file saved successfully.'})
    else:
        return jsonify({'status': 'error', 'message': 'Failed to save coupons file.'}), 500


@app.route('/delete_coupon', methods=['POST'])
@requires_auth
def delete_coupon():
    coupon_name = request.json.get('coupon_name')
    if not coupon_name:
        return jsonify({'status': 'error', 'message': 'Coupon name is required'}), 400

    if data_manager.delete_coupon(coupon_name):
        return jsonify({'status': 'success', 'message': f'Coupon {coupon_name} deleted.'})
    else:
        return jsonify({'status': 'error', 'message': 'Coupon not found or error deleting.'}), 404


@app.route('/delete_uid', methods=['POST'])
@requires_auth
def delete_uid():
    uid_to_delete = request.json.get('uid')
    if not uid_to_delete:
        return jsonify({'status': 'error', 'message': 'UID is required'}), 400

    if data_manager.delete_uid(uid_to_delete):
        return jsonify({'status': 'success', 'message': f'UID {uid_to_delete} deleted.'})
    else:
        return jsonify({'status': 'error', 'message': 'UID not found or error deleting.'}), 404


@app.route('/screenshots/<filename>')
@requires_auth
def get_screenshot(filename):
    """Serves the screenshot image."""
    return send_from_directory('screenshots', filename)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5001)
else:
    # Start the backup scheduler in a background thread when run with Gunicorn
    backup_thread = threading.Thread(target=backup_scheduler)
    backup_thread.daemon = True
    backup_thread.start()