# GEMINI.md

## Project Overview

This project is a Taobao price monitoring tool. It allows users to track the prices of products on Taobao, a popular Chinese e-commerce website. The application provides a web interface to add, remove, and view monitored products. It features a background scheduler that automatically scrapes the latest prices at regular intervals. When a price change is detected, the application sends an email notification to the user.

The project is built with the following technologies:

*   **Backend:** Python with Flask
*   **Web Scraping:** Playwright with the `playwright-stealth` library to avoid bot detection
*   **Database:** SQLite to store product information, price history, and application settings
*   **Scheduling:** The `schedule` library is used for periodic scraping.
*   **Frontend:** HTML, CSS, and JavaScript are used for the web interface.

## Building and Running

To run the project, follow these steps:

1.  **Create and activate a virtual environment:**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install the dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure email notifications (optional):**

    To receive price change notifications, set the following environment variables before starting the application. For Gmail, you may need to use an "App Password".

    ```bash
    export SMTP_HOST=smtp.example.com
    export SMTP_PORT=465
    export SMTP_USER=your_email@example.com
    export SMTP_PASSWORD=your_password_or_app_password
    ```

4.  **Run the application:**

    ```bash
    python app.py
    ```

    The application will be available at `http://127.0.0.1:5000`.

## Development Conventions

*   **Code Style:** The code follows the PEP 8 style guide for Python.
*   **Logging:** The application uses the `logging` module to log important events. Logs are stored in the `logs` directory, with a new subdirectory created for each run.
*   **Database:** The database schema is defined in `database.py`. The database is initialized when the application starts.
*   **Scraping:** The web scraping logic is located in `scraper.py`. It uses Playwright to control a headless browser and scrape product information.
*   **Notifications:** The email notification logic is in `notifier.py`. It uses `smtplib` to send emails.
*   **Frontend:** The frontend templates are located in the `templates` directory. Static assets such as CSS and JavaScript files are in the `static` directory.
