import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os

BASE_URL = "https://intelligence.streamlit.app"

def get_new_items(days=7):
    df = pd.read_csv("all_items.csv")
    df["Date added"] = pd.to_datetime(df["Date added"], utc=True, errors="coerce")
    cutoff = datetime.now(tz=df["Date added"].dt.tz) - timedelta(days=days)
    new_items = df[df["Date added"] >= cutoff].copy()
    new_items = new_items.sort_values("Date added", ascending=False)
    return new_items

def build_html_digest(df):
    today = datetime.now().strftime("%d %B %Y")
    count = len(df)

    if count == 0:
        return None

    grouped = df.groupby("Publication type")

    rows_html = ""
    for pub_type, group in grouped:
        rows_html += f"""
        <h3 style="color: #1a1a1a; border-bottom: 2px solid #5cb85c; padding-bottom: 6px; margin-top: 28px; font-family: Georgia, serif;">
            {pub_type} <span style="color: #888; font-size: 0.85em;">({len(group)})</span>
        </h3>
        """
        for _, row in group.iterrows():
            title     = str(row.get("Title", "")).strip()
            authors   = str(row.get("FirstName2", "")).strip()
            date_pub  = str(row.get("Date published", "")).strip()
            journal   = str(row.get("Journal", "")).strip()
            publisher = str(row.get("Publisher", "")).strip()
            zotero    = str(row.get("Zotero link", "")).strip()

            parent_key = zotero.rstrip("/").split("/")[-1] if zotero else ""
            item_url   = f"{BASE_URL}/?item={parent_key}" if parent_key else BASE_URL

            if journal and journal != "nan":
                source = f"<em>{journal}</em>"
            elif publisher and publisher != "nan":
                source = f"{publisher}"
            else:
                source = ""

            authors_display = authors if authors and authors != "nan" else "N/A"
            date_display    = date_pub if date_pub and date_pub != "nan" else "N/A"

            rows_html += f"""
            <div style="margin-bottom: 14px; padding: 14px 16px; background: #f8f8f8; border-left: 4px solid #5cb85c; border-radius: 0 4px 4px 0;">
                <a href="{item_url}" style="font-weight: bold; color: #1a1a1a; text-decoration: none; font-family: Georgia, serif; font-size: 1em; line-height: 1.4;">
                    {title}
                </a><br>
                <span style="color: #555; font-size: 0.88em; font-family: Arial, sans-serif;">
                    {authors_display} &nbsp;·&nbsp; {date_display}
                    {"&nbsp;·&nbsp;" + source if source else ""}
                </span><br>
                <a href="{item_url}" style="font-size: 0.82em; color: #5cb85c; text-decoration: none; font-family: Arial, sans-serif;">
                    View in IntelArchive →
                </a>
            </div>
            """

    # Logo as text-based header since SVG in email is unreliable
    html = f"""
    <html>
    <body style="margin: 0; padding: 0; background-color: #f4f4f4;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4;">
            <tr>
                <td align="center" style="padding: 30px 20px;">
                    <table width="640" cellpadding="0" cellspacing="0" style="max-width: 640px; width: 100%; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">

                        <!-- Header -->
                        <tr>
                            <td style="background-color: #1a1a1a; padding: 28px 32px;">
                                <table cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td style="padding-right: 4px;">
                                            <span style="font-family: Arial, sans-serif; font-size: 28px; font-weight: bold; color: #ffffff; letter-spacing: -0.5px;">Intel</span>
                                        </td>
                                        <td style="padding: 0 2px;">
                                            <span style="font-family: Arial, sans-serif; font-size: 28px; font-weight: bold; color: #5cb85c;">|</span>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td colspan="2">
                                            <span style="font-family: Arial, sans-serif; font-size: 28px; font-weight: bold; color: #ffffff; letter-spacing: -0.5px;">Archi</span><span style="font-family: Arial, sans-serif; font-size: 28px; font-weight: bold; color: #5cb85c;">v</span><span style="font-family: Arial, sans-serif; font-size: 28px; font-weight: bold; color: #ffffff; letter-spacing: -0.5px;">e</span>
                                        </td>
                                    </tr>
                                </table>
                                <p style="color: #aaaaaa; margin: 10px 0 0 0; font-size: 0.85em; font-family: Arial, sans-serif;">
                                    Intelligence Studies Database
                                </p>
                            </td>
                        </tr>

                        <!-- Digest title bar -->
                        <tr>
                            <td style="background-color: #5cb85c; padding: 12px 32px;">
                                <span style="color: #ffffff; font-family: Arial, sans-serif; font-size: 0.95em; font-weight: bold;">
                                    Weekly Digest &nbsp;·&nbsp; {today} &nbsp;·&nbsp; {count} new item{"s" if count != 1 else ""}
                                </span>
                            </td>
                        </tr>

                        <!-- Body -->
                        <tr>
                            <td style="padding: 28px 32px;">
                                <p style="font-family: Arial, sans-serif; color: #444; margin: 0 0 20px 0; font-size: 0.95em;">
                                    Here are the latest additions to the
                                    <a href="{BASE_URL}" style="color: #5cb85c; text-decoration: none;">IntelArchive Intelligence Studies Database</a>.
                                </p>

                                {rows_html}
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #1a1a1a; padding: 20px 32px; text-align: center;">
                                <p style="font-family: Arial, sans-serif; font-size: 0.78em; color: #888; margin: 0;">
                                    You are receiving this because you are subscribed to the
                                    <a href="https://groups.google.com/g/intelarchive" style="color: #5cb85c; text-decoration: none;">IntelArchive mailing list</a>.
                                </p>
                                <p style="font-family: Arial, sans-serif; font-size: 0.78em; color: #888; margin: 8px 0 0 0;">
                                    <a href="{BASE_URL}" style="color: #5cb85c; text-decoration: none;">Visit IntelArchive</a>
                                </p>
                            </td>
                        </tr>

                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    return html

def send_digest():
    new_items = get_new_items(days=7)
    count     = len(new_items)

    if count == 0:
        print("No new items this week. Skipping digest.")
        return

    html = build_html_digest(new_items)
    if not html:
        print("Nothing to send.")
        return

    # Email config from environment variables
    smtp_server   = os.environ["SMTP_SERVER"]       # e.g. smtp.gmail.com
    smtp_port     = int(os.environ["SMTP_PORT"])    # e.g. 587
    smtp_user     = os.environ["SMTP_USER"]         # your gmail address
    smtp_password = os.environ["SMTP_PASSWORD"]     # app password
    to_address    = os.environ["DIGEST_TO"]         # Google Group email

    today = datetime.now().strftime("%d %B %Y")
    subject = f"IntelArchive Weekly Digest — {count} new item{'s' if count != 1 else ''} · {today}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = smtp_user
    msg["To"]      = to_address
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_address, msg.as_string())

    print(f"Digest sent: {count} new items to {to_address}")

if __name__ == "__main__":
    send_digest()