import logging
import sqlite3
import database
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import scraper
import sys
import os
import schedule
import time
import threading

# --- Advanced Logging Configuration ---
def setup_logging():
    # ... (logging setup remains the same)
    run_timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_dir = os.path.join('logs', f'run_{run_timestamp}')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_filename = os.path.join(log_dir, 'app.log')
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s : %(message)s')
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

setup_logging()

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- Scheduler Functions ---
def perform_scheduled_scrapes():
    with app.app_context(): # Need app context to access logger etc.
        logging.info("--- Starting scheduled scrape run --- ")
        conn = sqlite3.connect(database.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, url, current_price FROM products")
        products_to_scrape = cursor.fetchall()
        conn.close()

        for product in products_to_scrape:
            product_id, url, old_price = product
            logging.info(f"Scheduled scrape for product ID: {product_id}, URL: {url}")
            # Scheduled scrapes are always headless
            name, new_price = scraper.scrape_product(url, headless=True)
            
            if new_price and new_price != old_price:
                logging.info(f"Price change detected for product ID {product_id}! Old: {old_price}, New: {new_price}")
                
                # --- Send Email Notification ---
                conn_settings = sqlite3.connect(database.DB_PATH)
                cursor_settings = conn_settings.cursor()
                cursor_settings.execute("SELECT value FROM settings WHERE key = ?", ('email',))
                email_row = cursor_settings.fetchone()
                conn_settings.close()
                recipient_email = email_row[0] if email_row and email_row[0] else None
                if recipient_email:
                    # Use the product name from the database as it's more reliable
                    conn_prod = sqlite3.connect(database.DB_PATH)
                    cursor_prod = conn_prod.cursor()
                    cursor_prod.execute("SELECT name FROM products WHERE id = ?", (product_id,))
                    product_name = cursor_prod.fetchone()[0]
                    conn_prod.close()
                    notifier.send_email_notification(recipient_email, product_name, old_price, new_price, url)
                else:
                    logging.warning("Price change detected, but no recipient email is configured in settings.")
                # --------------------------------
                
                # Update database
                conn_update = sqlite3.connect(database.DB_PATH)
                cursor_update = conn_update.cursor()
                cursor_update.execute("UPDATE products SET current_price = ?, last_check_time = ? WHERE id = ?", (new_price, datetime.now(), product_id))
                cursor_update.execute("INSERT INTO price_history (product_id, price, timestamp) VALUES (?, ?, ?)", (product_id, new_price, datetime.now()))
                conn_update.commit()
                conn_update.close()
            elif not new_price:
                logging.warning(f"Scheduled scrape for product ID {product_id} failed to get a price.")
            else:
                logging.info(f"No price change for product ID {product_id}. Price is still {new_price}.")
        logging.info("--- Scheduled scrape run finished --- ")

def run_scheduler():
    # Initial setup of the schedule based on DB settings
    conn = sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", ('frequency_hours',))
    freq_row = cursor.fetchone()
    conn.close()
    # Default to 1 hour if not set
    frequency = int(freq_row[0]) if freq_row and freq_row[0] else 1
    logging.info(f"Scheduler starting. Scrape frequency set to every {frequency} hour(s).")
    
    schedule.every(frequency).hours.do(perform_scheduled_scrapes)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

# --- App Initialization ---
with app.app_context():
    logging.info("Initializing database...")
    database.init_db()
    logging.info("Database initialized.")

# --- App Routes ---
@app.route('/')
def index():
    # ... (index route remains the same)
    try:
        logging.debug("Accessing index route.")
        conn = sqlite3.connect(database.DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products ORDER BY id DESC")
        products = cursor.fetchall()
        conn.close()
        logging.debug("Successfully fetched products.")
        return render_template('index.html', products=products)
    except Exception as e:
        logging.error(f"Error in index route: {e}", exc_info=True)
        return "An internal error occurred.", 500

@app.route('/add', methods=['POST'])
def add_product():
    # ... (add_product remains the same)
    product_url = request.form.get('product_url')
    if product_url:
        logging.info(f"Adding product URL to database: {product_url}")
        conn = sqlite3.connect(database.DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO products (url, name) VALUES (?, ?)", (product_url, 'Pending scrape'))
            conn.commit()
        except sqlite3.IntegrityError:
            logging.warning(f"Product URL {product_url} already exists.")
        finally:
            conn.close()
    return redirect(url_for('index'))

@app.route('/scrape/<int:product_id>', methods=['POST'])
def scrape_product_route(product_id):
    # ... (scrape_product_route is modified to call with headless=False)
    logging.info(f"Manual scrape requested for product ID: {product_id}")
    conn = sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT url FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    conn.close()

    if product:
        # Manual scrapes are NOT headless, so user can see the browser
        name, price = scraper.scrape_product(product[0], headless=False)
        logging.info(f"Scraped data for ID {product_id}: Name={name}, Price={price}")
        
        conn = sqlite3.connect(database.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET name = ?, current_price = ?, last_check_time = ? WHERE id = ?", (name, price, datetime.now(), product_id))
        if price:
            cursor.execute("INSERT INTO price_history (product_id, price, timestamp) VALUES (?, ?, ?)", (product_id, price, datetime.now()))
        conn.commit()
        conn.close()
    else:
        logging.warning(f"Scrape requested for non-existent product ID: {product_id}")
    return redirect(url_for('index'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    # ... (settings route remains the same)
    conn = sqlite3.connect(database.DB_PATH)
    cursor = conn.cursor()
    if request.method == 'POST':
        proxy_url = request.form.get('proxy_url')
        email = request.form.get('email')
        frequency = request.form.get('frequency_hours')
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('proxy_url', proxy_url))
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('email', email))
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('frequency_hours', frequency))
        conn.commit()
        logging.info(f"Settings updated: proxy_url={proxy_url}, email={email}, frequency={frequency}h")
        flash('Settings saved successfully!', 'success')
        return redirect(url_for('settings'))
    cursor.execute("SELECT key, value FROM settings")
    settings_data = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    return render_template('settings.html', settings=settings_data)

@app.route('/api/price_history/<int:product_id>')
def price_history_api(product_id):
    try:
        conn = sqlite3.connect(database.DB_PATH)
        cursor = conn.cursor()
        # Timestamps are stored as strings, so we don't need to format them further
        cursor.execute("SELECT strftime('%Y-%m-%d %H:%M', timestamp), price FROM price_history WHERE product_id = ? ORDER BY timestamp ASC", (product_id,))
        history = cursor.fetchall()
        conn.close()
        # Format data for Chart.js
        labels = [row[0] for row in history]
        data = [row[1] for row in history]
        return jsonify({'labels': labels, 'data': data})
    except Exception as e:
        logging.error(f"Error in price_history_api for ID {product_id}: {e}", exc_info=True)
        return jsonify({'error': 'Could not fetch price history'}), 500

@app.route('/remove/<int:product_id>', methods=['POST'])
def remove_product(product_id):
    # ... (remove_product remains the same)
    try:
        logging.info(f"Removing product with ID: {product_id}")
        conn = sqlite3.connect(database.DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM price_history WHERE product_id = ?", (product_id,))
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        conn.close()
        logging.info(f"Successfully removed product ID: {product_id}")
    except Exception as e:
        logging.error(f"Error in remove_product route for ID {product_id}: {e}", exc_info=True)
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Start the scheduler in a background thread
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    # Run the Flask app
    app.run(debug=True, use_reloader=False, host='0.0.0.0')