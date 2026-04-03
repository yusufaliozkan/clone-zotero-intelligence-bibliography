import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import os

BASE_URL = "https://intelligence.streamlit.app"

def get_new_items(days=7):
    import os
    # Works whether run from repo root or database_update folder
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    df = pd.read_csv(os.path.join(base_dir, "all_items.csv"))
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

    # Group by publication type
    grouped = df.groupby("Publication type")

    rows_html = ""
    for pub_type, group in grouped:
        rows_html += f"""
        <h3 style="color: #c0392b; border-bottom: 1px solid #eee; padding-bottom: 4px;">
            {pub_type} ({len(group)})
        </h3>
        """
        for _, row in group.iterrows():
            title     = str(row.get("Title", "")).strip()
            authors   = str(row.get("FirstName2", "")).strip()
            date_pub  = str(row.get("Date published", "")).strip()
            journal   = str(row.get("Journal", "")).strip()
            publisher = str(row.get("Publisher", "")).strip()
            zotero    = str(row.get("Zotero link", "")).strip()

            # Build item URL
            parent_key = zotero.rstrip("/").split("/")[-1] if zotero else ""
            item_url   = f"{BASE_URL}/?item={parent_key}" if parent_key else BASE_URL

            # Source line
            if journal and journal != "nan":
                source = f"<em>{journal}</em>"
            elif publisher and publisher != "nan":
                source = f"{publisher}"
            else:
                source = ""

            authors_display = authors if authors and authors != "nan" else "N/A"
            date_display    = date_pub if date_pub and date_pub != "nan" else "N/A"

            rows_html += f"""
            <div style="margin-bottom: 16px; padding: 12px; background: #f9f9f9; border-left: 3px solid #c0392b; border-radius: 4px;">
                <a href="{item_url}" style="font-weight: bold; color: #2c3e50; text-decoration: none;">
                    {title}
                </a><br>
                <span style="color: #555; font-size: 0.9em;">
                    {authors_display} · {date_display}
                    {"· " + source if source else ""}
                </span><br>
                <a href="{item_url}" style="font-size: 0.85em; color: #c0392b;">
                    View in IntelArchive →
                </a>
            </div>
            """

    html = f"""
    <html>
    <body style="font-family: Georgia, serif; max-width: 700px; margin: auto; padding: 20px; color: #2c3e50;">
        <div style="background: #c0392b; padding: 20px; border-radius: 6px; margin-bottom: 24px;">
            <h1 style="color: white; margin: 0; font-size: 1.4em;">
                📚 IntelArchive Weekly Digest
            </h1>
            <p style="color: #f5b7b1; margin: 6px 0 0 0; font-size: 0.9em;">
                {count} new item{"s" if count != 1 else ""} added · Week of {today}
            </p>
        </div>

        <p>
            Here are the latest additions to the 
            <a href="{BASE_URL}" style="color: #c0392b;">IntelArchive Intelligence Studies Database</a>.
        </p>

        {rows_html}

        <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
        <p style="font-size: 0.8em; color: #999; text-align: center;">
            You are receiving this because you are subscribed to the 
            <a href="https://groups.google.com/g/intelarchive" style="color: #c0392b;">
                IntelArchive mailing list
            </a>.<br>
            <a href="{BASE_URL}" style="color: #c0392b;">Visit IntelArchive</a>
        </p>
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