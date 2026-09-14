IMAP_SERVER = "imap.gmail.com"
IMAP_PORT = 993

from imap_tools import MailBox
from bs4 import BeautifulSoup
import csv
from pathlib import Path


def download_emails(email_address: str, app_password: str, results_file_name: str = "emails.csv"):
    file_path = Path(__file__).parent / "data" / results_file_name
    with MailBox(IMAP_SERVER, IMAP_PORT).login(email_address, app_password) as mailbox:
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["uid", "from", "subject", "date", "body"])
            for msg in mailbox.fetch(limit=20000, reverse=True, bulk=1000):
                msg_html = BeautifulSoup(msg.html)
                msg_body = " ".join(msg_html.get_text("\n", strip=True).split()) or msg.text
                row = [msg.uid, msg.from_, msg.subject, msg.date_str, msg_body]
                writer.writerow(row)


def main():
    email_address = input("Enter your Gmail address: ")
    app_password = input("Enter your Gmail app password: ")
    download_emails(email_address, app_password)


if __name__ == "__main__":
    main()
