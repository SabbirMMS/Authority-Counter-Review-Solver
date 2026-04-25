from __future__ import annotations

import smtplib
from email.mime.text import MIMEText


class EmailService:
    def __init__(
        self,
        host: str,
        port: int,
        username: str | None,
        password: str | None,
        from_email: str,
        use_tls: bool,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from_email = from_email
        self._use_tls = use_tls

    def send_html(
        self,
        to_email: str,
        cc_emails: list[str],
        subject: str,
        html_content: str,
    ) -> None:
        msg = MIMEText(html_content, "html", "utf-8")
        msg["Subject"] = subject
        msg["From"] = self._from_email
        msg["To"] = to_email
        if cc_emails:
            msg["Cc"] = ", ".join(cc_emails)

        recipients = [to_email, *cc_emails]

        with smtplib.SMTP(self._host, self._port, timeout=30) as smtp:
            if self._use_tls:
                smtp.starttls()
            if self._username and self._password:
                smtp.login(self._username, self._password)
            smtp.sendmail(self._from_email, recipients, msg.as_string())
