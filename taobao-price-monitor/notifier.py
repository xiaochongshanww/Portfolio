import smtplib
import os
import logging
from email.message import EmailMessage

logger = logging.getLogger(__name__)

def send_email_notification(recipient_email: str, product_name: str, old_price: float, new_price: float, product_url: str):
    """Sends an email notification about a price change."""
    # SMTP configuration from environment variables
    smtp_host = os.getenv('SMTP_HOST')
    smtp_port = os.getenv('SMTP_PORT')
    smtp_user = os.getenv('SMTP_USER')
    smtp_password = os.getenv('SMTP_PASSWORD')

    if not all([smtp_host, smtp_port, smtp_user, smtp_password]):
        logger.warning("SMTP environment variables not fully configured. Skipping email notification.")
        return

    try:
        smtp_port = int(smtp_port)
    except (ValueError, TypeError):
        logger.error(f"Invalid SMTP_PORT: {smtp_port}. Must be an integer.")
        return

    # Create the email message
    msg = EmailMessage()
    msg['Subject'] = f"Price Drop Alert: '{product_name[:30]}...'"
    msg['From'] = smtp_user
    msg['To'] = recipient_email

    price_diff = new_price - old_price
    change_type = "dropped" if price_diff < 0 else "increased"

    # Plain text body
    text_body = f"""
    Hello,

    A price change has been detected for a product you are monitoring.

    Product: {product_name}
    Old Price: ¥{old_price:.2f}
    New Price: ¥{new_price:.2f} (Price {change_type} by ¥{abs(price_diff):.2f})

    You can view the product here:
    {product_url}

    Regards,
    Your Price Monitor Bot
    """
    msg.set_content(text_body)

    # HTML body
    html_body = f"""
    <html>
        <body>
            <p>Hello,</p>
            <p>A price change has been detected for a product you are monitoring.</p>
            <hr>
            <p><b>Product:</b> {product_name}</p>
            <p><b>Old Price:</b> ¥{old_price:.2f}</p>
            <p><b>New Price:</b> <strong style='color: {"green" if change_type == "dropped" else "red"};'>¥{new_price:.2f}</strong> (Price {change_type} by ¥{abs(price_diff):.2f})</p>
            <p><a href="{product_url}">Click here to view the product</a></p>
            <hr>
            <p>Regards,<br>Your Price Monitor Bot</p>
        </body>
    </html>
    """
    msg.add_alternative(html_body, subtype='html')

    # Send the email
    try:
        logger.info(f"Sending price change notification to {recipient_email}")
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        logger.info("Email sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send email: {e}", exc_info=True)
