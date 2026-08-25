import os
import imaplib
import email
from email.header import decode_header
from langchain_core.tools import tool
import json

def create_email_check_tool():
    @tool
    def check_inbox(sender_email: str = "") -> str:
        """Check Gmail inbox for unread replies from a specific supplier or stakeholders.
        
        Args:
            sender_email: Optional email address of the supplier to filter by. Leave blank to check all unread mail.
        """
        imap_host = os.getenv("IMAP_HOST", "imap.gmail.com")
        imap_port = int(os.getenv("IMAP_PORT", "993"))
        username = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASSWORD")

        if not username or not password:
            return json.dumps({"status": "error", "message": "IMAP/SMTP credentials not configured."})

        found_messages = []

        try:
            mail = imaplib.IMAP4_SSL(imap_host, imap_port)
            mail.login(username, password)
            mail.select("inbox")

            search_criteria = '(UNSEEN)'
            if sender_email:
                search_criteria = f'(UNSEEN FROM "{sender_email}")'

            status, messages = mail.search(None, search_criteria)
            if status != 'OK' or not messages[0]:
                mail.logout()
                return json.dumps({"status": "no_new_messages", "message": f"No unread messages found{f' from {sender_email}' if sender_email else ''}."})

            for num in messages[0].split():
                res, msg_data = mail.fetch(num, '(RFC822)')
                if res != 'OK':
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        subject_header = decode_header(msg["Subject"])[0]
                        subject = subject_header[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(subject_header[1] or "utf-8", errors="ignore")

                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")

                        found_messages.append({
                            "from": msg.get("From"),
                            "subject": subject,
                            "body_preview": body[:500] + ("..." if len(body) > 500 else "")
                        })

            mail.logout()
            return json.dumps({
                "status": "success",
                "new_messages_count": len(found_messages),
                "messages": found_messages
            }, indent=2)

        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    return [check_inbox]