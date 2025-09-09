import logging
import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

import config
import data_manager
from app import running_threads, thread_lock, worker_wrapper, session_semaphore

# --- Conversation States ---
(
    CHOOSING_MAIN_MENU,
    CHOOSING_UID_MENU,
    GETTING_UID_TO_ADD,
    GETTING_COMMENT_FOR_UID,
    CHOOSING_UID_TO_DELETE,
    CONFIRMING_UID_DELETE,
    CHOOSING_COUPON_MENU,
    GETTING_COUPON_TO_ADD,
    CHOOSING_COUPON_TO_DELETE,
    CONFIRMING_COUPON_DELETE,
    SELECTING_UIDS_FOR_RUN,
    SELECTING_COUPONS_FOR_RUN,
    CHOOSING_LOG_TYPE,
    CHOOSING_LOG_FILE,
    CHOOSING_COUPON_LOG_FILE,
    CHOOSING_MONITOR_SESSION,
) = range(16)

# --- Main Menu ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the conversation and shows the main menu."""
    if str(update.effective_chat.id) != config.TELEGRAM_CHAT_ID:
        await update.message.reply_text("You are not authorized to use this bot.")
        return ConversationHandler.END

    reply_keyboard = [
        ["1. UID Management"],
        ["2. Coupon Management"],
        ["3. Run Automation"],
        ["4. View Logs"],
        ["5. Monitoring"],
        ["/cancel"],
    ]
    await update.message.reply_text(
        "Welcome to the TopHeroes Bot! Please choose an option:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return CHOOSING_MAIN_MENU

# --- UID Management ---
async def uid_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [["1. Add UID"], ["2. Delete UID"], ["Back to Main Menu"]]
    await update.message.reply_text(
        "UID Management:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    uids = data_manager.get_uids_list()
    if not uids:
        await update.message.reply_text("No UIDs found.")
    else:
        message = "Current UIDs:\n" + "\n".join(f"- {u['uid']} ({u['comment']})" for u in uids)
        await update.message.reply_text(message)
    return CHOOSING_UID_MENU

async def uid_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Please enter the new UID:", reply_markup=ReplyKeyboardRemove())
    return GETTING_UID_TO_ADD

async def get_uid_to_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_uid'] = update.message.text
    await update.message.reply_text("Please enter the user's name (comment):")
    return GETTING_COMMENT_FOR_UID

async def get_comment_for_uid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid = context.user_data.pop('new_uid')
    comment = update.message.text
    if data_manager.add_uid(uid, comment):
        await update.message.reply_text(f"UID {uid} ({comment}) added successfully.")
    else:
        await update.message.reply_text("Failed to add UID.")
    return await uid_menu(update, context)

async def uid_delete_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uids = data_manager.get_uids_list()
    if not uids:
        await update.message.reply_text("No UIDs to delete.")
        return await uid_menu(update, context)
    
    context.user_data['uids_to_delete'] = uids
    message = "Select the UID to delete:\n"
    message += "\n".join(f"{i+1}. {u['uid']} ({u['comment']})" for i, u in enumerate(uids))
    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
    return CHOOSING_UID_TO_DELETE

async def choose_uid_to_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        choice = int(update.message.text) - 1
        uids = context.user_data['uids_to_delete']
        if 0 <= choice < len(uids):
            context.user_data['uid_to_delete'] = uids[choice]
            reply_keyboard = [["Yes, delete it"], ["No, go back"]]
            await update.message.reply_text(
                f"Are you sure you want to delete {uids[choice]['uid']}?",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
            )
            return CONFIRMING_UID_DELETE
        else:
            await update.message.reply_text("Invalid choice. Please try again.")
            return CHOOSING_UID_TO_DELETE
    except (ValueError, IndexError):
        await update.message.reply_text("Invalid input. Please enter a number.")
        return CHOOSING_UID_TO_DELETE

async def confirm_uid_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.lower() == "yes, delete it":
        uid_info = context.user_data.pop('uid_to_delete')
        if data_manager.delete_uid(uid_info['uid']):
            await update.message.reply_text(f"UID {uid_info['uid']} deleted.")
        else:
            await update.message.reply_text("Failed to delete UID.")
    context.user_data.pop('uids_to_delete', None)
    return await uid_menu(update, context)


# --- Coupon Management ---
async def coupon_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [["1. Add Coupon"], ["2. Delete Coupon"], ["Back to Main Menu"]]
    await update.message.reply_text(
        "Coupon Management:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    coupons = data_manager.get_all_coupons()
    if not coupons:
        await update.message.reply_text("No coupons found.")
    else:
        await update.message.reply_text("Current Coupons:\n" + "\n".join(f"- {c}" for c in coupons))
    return CHOOSING_COUPON_MENU

async def coupon_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Please enter the new coupon code:", reply_markup=ReplyKeyboardRemove())
    return GETTING_COUPON_TO_ADD

async def get_coupon_to_add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    coupon = update.message.text
    if data_manager.add_coupon(coupon):
        await update.message.reply_text(f"Coupon '{coupon}' added successfully.")
    else:
        await update.message.reply_text("Failed to add coupon.")
    return await coupon_menu(update, context)

async def coupon_delete_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    coupons = data_manager.get_all_coupons()
    if not coupons:
        await update.message.reply_text("No coupons to delete.")
        return await coupon_menu(update, context)
    
    context.user_data['coupons_to_delete'] = coupons
    message = "Select the coupon to delete:\n" + "\n".join(f"{i+1}. {c}" for i, c in enumerate(coupons))
    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
    return CHOOSING_COUPON_TO_DELETE

async def choose_coupon_to_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        choice = int(update.message.text) - 1
        coupons = context.user_data['coupons_to_delete']
        if 0 <= choice < len(coupons):
            context.user_data['coupon_to_delete'] = coupons[choice]
            reply_keyboard = [["Yes, delete it"], ["No, go back"]]
            await update.message.reply_text(
                f"Are you sure you want to delete '{coupons[choice]}'?",
                reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
            )
            return CONFIRMING_COUPON_DELETE
        else:
            await update.message.reply_text("Invalid choice.")
            return CHOOSING_COUPON_TO_DELETE
    except (ValueError, IndexError):
        await update.message.reply_text("Invalid input.")
        return CHOOSING_COUPON_TO_DELETE

async def confirm_coupon_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.lower() == "yes, delete it":
        coupon = context.user_data.pop('coupon_to_delete')
        if data_manager.delete_coupon(coupon):
            await update.message.reply_text(f"Coupon '{coupon}' deleted.")
        else:
            await update.message.reply_text("Failed to delete coupon.")
    context.user_data.pop('coupons_to_delete', None)
    return await coupon_menu(update, context)


# --- Run Automation ---
async def run_automation_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uids = data_manager.get_uids_list()
    if not uids:
        await update.message.reply_text("No UIDs configured. Please add UIDs first.", reply_markup=ReplyKeyboardRemove())
        return await start(update, context)
    
    context.user_data['uids_for_run'] = uids
    message = "Select UIDs to run (e.g., 1, 3-5):\n1. All UIDs\n"
    message += "\n".join(f"{i+2}. {u['uid']} ({u['comment']})" for i, u in enumerate(uids))
    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
    return SELECTING_UIDS_FOR_RUN

async def select_uids_for_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # Simplified: user provides comma-separated list of numbers
    try:
        choices = [int(c.strip()) for c in update.message.text.split(',')]
        uids_for_run = context.user_data['uids_for_run']
        selected_uids = []

        if 1 in choices:
            selected_uids = uids_for_run
        else:
            for choice in choices:
                if 2 <= choice <= len(uids_for_run) + 1:
                    selected_uids.append(uids_for_run[choice - 2])
        
        if not selected_uids:
            await update.message.reply_text("No valid UIDs selected.")
            return SELECTING_UIDS_FOR_RUN

        context.user_data['selected_uids_for_run'] = [f"{u['uid']}_{u['comment']}" for u in selected_uids]
        
        coupons = data_manager.get_all_coupons()
        if not coupons:
            await update.message.reply_text("No coupons configured. Please add coupons first.")
            return await start(update, context)

        context.user_data['coupons_for_run'] = coupons
        message = "Select coupons to use (e.g., 1, 3):\n1. All Coupons\n"
        message += "\n".join(f"{i+2}. {c}" for i, c in enumerate(coupons))
        await update.message.reply_text(message)
        return SELECTING_COUPONS_FOR_RUN

    except ValueError:
        await update.message.reply_text("Invalid format. Please enter numbers separated by commas.")
        return SELECTING_UIDS_FOR_RUN

async def select_coupons_for_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        choices = [int(c.strip()) for c in update.message.text.split(',')]
        coupons_for_run = context.user_data['coupons_for_run']
        selected_coupons = []

        if 1 in choices:
            selected_coupons = coupons_for_run
        else:
            for choice in choices:
                if 2 <= choice <= len(coupons_for_run) + 1:
                    selected_coupons.append(coupons_for_run[choice - 2])

        if not selected_coupons:
            await update.message.reply_text("No valid coupons selected.")
            return SELECTING_COUPONS_FOR_RUN

        selected_uids = context.user_data.pop('selected_uids_for_run')
        
        # This part is synchronous but should be quick
        uids_map = {f"{u['uid']}_{u['comment']}": u for u in data_manager.get_uids_list()}
        started_count = 0
        with thread_lock:
            for base_filename in selected_uids:
                if base_filename in uids_map and base_filename not in running_threads:
                    uid_info = uids_map[base_filename]
                    running_threads[base_filename] = {
                        'status': 'Queued', 'log_preview': 'Waiting for session...',
                        'display_name': f"{uid_info['uid']} ({uid_info['comment']})", 'session_id': None
                    }
                    # Offload the actual work to a thread
                    context.application.create_task(
                        run_worker_in_thread(uid_info['uid'], uid_info['comment'], selected_coupons, base_filename)
                    )
                    started_count += 1
        
        await update.message.reply_text(f"Started automation for {started_count} UIDs.", reply_markup=ReplyKeyboardRemove())
        return await start(update, context)

    except ValueError:
        await update.message.reply_text("Invalid format. Please enter numbers separated by commas.")
        return SELECTING_COUPONS_FOR_RUN

async def run_worker_in_thread(uid, comment, coupons, base_filename):
    """Helper to run the blocking worker_wrapper in a separate thread."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, worker_wrapper, uid, comment, coupons, base_filename
    )

# --- Log Viewing ---
async def log_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [["1. View App Logs"], ["2. View Coupon Logs"], ["Back to Main Menu"]]
    await update.message.reply_text(
        "Log Viewer:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return CHOOSING_LOG_TYPE

async def choose_log_file_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    log_files = sorted([f for f in os.listdir('logs') if f.endswith('.log')], reverse=True)
    if not log_files:
        await update.message.reply_text("No app logs found.")
        return await log_menu(update, context)
    
    context.user_data['log_files'] = log_files
    message = "Select a log file to view:\n" + "\n".join(f"{i+1}. {f}" for i, f in enumerate(log_files))
    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
    return CHOOSING_LOG_FILE

async def show_log_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        choice = int(update.message.text) - 1
        log_files = context.user_data.pop('log_files')
        if 0 <= choice < len(log_files):
            filepath = os.path.join('logs', log_files[choice])
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            # Split content if too long for a single message
            for i in range(0, len(content), 4096):
                await update.message.reply_text(content[i:i+4096])
        else:
            await update.message.reply_text("Invalid choice.")
    except (ValueError, IndexError):
        await update.message.reply_text("Invalid input.")
    
    return await log_menu(update, context)

async def choose_coupon_log_file_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    log_files = sorted([f for f in os.listdir('coupon_logs') if f.endswith('.txt')], reverse=True)
    if not log_files:
        await update.message.reply_text("No coupon logs found.")
        return await log_menu(update, context)
        
    context.user_data['coupon_log_files'] = log_files
    message = "Select a coupon log file to view:\n" + "\n".join(f"{i+1}. {f}" for i, f in enumerate(log_files))
    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
    return CHOOSING_COUPON_LOG_FILE

async def show_coupon_log_content(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        choice = int(update.message.text) - 1
        log_files = context.user_data.pop('coupon_log_files')
        if 0 <= choice < len(log_files):
            filepath = os.path.join('coupon_logs', log_files[choice])
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            for i in range(0, len(content), 4096):
                await update.message.reply_text(content[i:i+4096])
        else:
            await update.message.reply_text("Invalid choice.")
    except (ValueError, IndexError):
        await update.message.reply_text("Invalid input.")

    return await log_menu(update, context)


# --- Monitoring ---
async def monitoring_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    with thread_lock:
        active_sessions = {k: v for k, v in running_threads.items() if v.get('session_id')}
    
    if not active_sessions:
        await update.message.reply_text("No active Selenium sessions.", reply_markup=ReplyKeyboardRemove())
        return await start(update, context)

    context.user_data['active_sessions'] = list(active_sessions.values())
    message = "Select a session to get the link:\n"
    message += "\n".join(f"{i+1}. {s['display_name']} ({s['status']})" for i, s in enumerate(active_sessions.values()))
    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
    return CHOOSING_MONITOR_SESSION

async def show_monitoring_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        choice = int(update.message.text) - 1
        sessions = context.user_data.pop('active_sessions')
        if 0 <= choice < len(sessions):
            session = sessions[choice]
            url = f"{config.SELENIUM_HUB_URL}/ui/#/session/{session['session_id']}"
            await update.message.reply_text(f"Session link for {session['display_name']}:\n{url}")
        else:
            await update.message.reply_text("Invalid choice.")
    except (ValueError, IndexError):
        await update.message.reply_text("Invalid input.")
        
    return await start(update, context)


# --- General ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    context.user_data.clear()
    await update.message.reply_text(
        "Operation cancelled.", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Clears user data and returns to the main menu."""
    context.user_data.clear()
    return await start(update, context)

def main() -> None:
    """Run the bot."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logging.warning("Telegram bot token or chat ID is not configured. Bot will not start.")
        return

    application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), CommandHandler("help", start)],
        states={
            CHOOSING_MAIN_MENU: [
                MessageHandler(filters.Regex("^1\\. UID Management$"), uid_menu),
                MessageHandler(filters.Regex("^2\\. Coupon Management$"), coupon_menu),
                MessageHandler(filters.Regex("^3\\. Run Automation$"), run_automation_start),
                MessageHandler(filters.Regex("^4\\. View Logs$"), log_menu),
                MessageHandler(filters.Regex("^5\\. Monitoring$"), monitoring_start),
            ],
            # UID States
            CHOOSING_UID_MENU: [
                MessageHandler(filters.Regex("^1\\. Add UID$"), uid_add_start),
                MessageHandler(filters.Regex("^2\\. Delete UID$"), uid_delete_start),
                MessageHandler(filters.Regex("^Back to Main Menu$"), back_to_main_menu),
            ],
            GETTING_UID_TO_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_uid_to_add)],
            GETTING_COMMENT_FOR_UID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_comment_for_uid)],
            CHOOSING_UID_TO_DELETE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_uid_to_delete)],
            CONFIRMING_UID_DELETE: [MessageHandler(filters.Regex("^(Yes, delete it|No, go back)$"), confirm_uid_delete)],
            # Coupon States
            CHOOSING_COUPON_MENU: [
                MessageHandler(filters.Regex("^1\\. Add Coupon$"), coupon_add_start),
                MessageHandler(filters.Regex("^2\\. Delete Coupon$"), coupon_delete_start),
                MessageHandler(filters.Regex("^Back to Main Menu$"), back_to_main_menu),
            ],
            GETTING_COUPON_TO_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_coupon_to_add)],
            CHOOSING_COUPON_TO_DELETE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_coupon_to_delete)],
            CONFIRMING_COUPON_DELETE: [MessageHandler(filters.Regex("^(Yes, delete it|No, go back)$"), confirm_coupon_delete)],
            # Run States
            SELECTING_UIDS_FOR_RUN: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_uids_for_run)],
            SELECTING_COUPONS_FOR_RUN: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_coupons_for_run)],
            # Log States
            CHOOSING_LOG_TYPE: [
                MessageHandler(filters.Regex("^1\\. View App Logs$"), choose_log_file_start),
                MessageHandler(filters.Regex("^2\\. View Coupon Logs$"), choose_coupon_log_file_start),
                MessageHandler(filters.Regex("^Back to Main Menu$"), back_to_main_menu),
            ],
            CHOOSING_LOG_FILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, show_log_content)],
            CHOOSING_COUPON_LOG_FILE: [MessageHandler(filters.TEXT & ~filters.COMMAND, show_coupon_log_content)],
            # Monitoring States
            CHOOSING_MONITOR_SESSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, show_monitoring_link)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    
    logging.info("Starting Telegram bot...")
    application.run_polling()

if __name__ == "__main__":
    # This allows running the bot directly for testing
    import asyncio
    # A basic logger for testing
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    main()
