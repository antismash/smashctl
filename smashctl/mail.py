"""Email sending"""
from email.mime.text import MIMEText
import smtplib
import os
from smashctl.common import AntismashRunError
from smashctl.messages import (
    message_template,
    success_template,
    failure_template,
)


class MailConfig:
    __slots__ = (
        'base_url',
        'configured',
        'encrypt',
        'password',
        'port',
        'sender',
        'server',
        'support',
        'tool',
        'username',
    )

    @classmethod
    def from_env(cls):
        """Initialize from environment variables"""
        config = cls()
        server = os.environ.get("SMASHCTL_EMAIL_HOST")
        if not server:
            config.configured = False
            return config

        config.base_url = os.environ.get("SMASHCTL_BASE_URL", "https://antismash.secondarymetabolites.org")
        config.encrypt = os.environ.get("SMASHCTL_EMAIL_ENCRYPT", "no")
        config.password = os.environ.get("SMASHCTL_EMAIL_PASSWORD", "")
        config.port = os.environ.get("SMASHCTL_EMAIL_PORT", 587)
        config.sender = os.environ.get("SMASHCTL_EMAIL_FROM", "noreply@secondarymetabolites.org")
        config.server = server
        config.support = os.environ.get("SMASHCTL_EMAIL_SUPPORT", "antismash@secondarymetabolites.org")
        config.tool = os.environ.get("SMASHCTL_TOOL_NAME", "antiSMASH")
        config.username = os.environ.get("SMASHCTL_EMAIL_USER", "")

        config.configured = True
        return config


    @classmethod
    def from_args(cls, args):
        """Initialize from an argparse.Namespace"""
        config = cls()
        if "server" not in args or not args.server:
            config.configured = False
            return config

        config.base_url = args.base_url
        config.encrypt = args.encrypt
        config.password = args.password
        config.port = args.port
        config.sender = args.sender
        config.server = args.server
        config.support = args.support
        config.tool = args.tool
        config.username = args.username

        config.configured = True
        return config


def send_mail(mail_conf, job):
    """Send an email about a job"""
    if job.state == 'done':
        action_string = success_template.format(j=job, c=mail_conf)
    else:
        action_string = failure_template.format(c=mail_conf, errors=job.status)

    message_text = message_template.format(j=job, c=mail_conf, action_string=action_string)

    message = MIMEText(message_text)
    message['From'] = mail_conf.sender
    message['To'] = job.email
    message['Subject'] = "Your {c.tool} job {j.job_id} finished.".format(j=job, c=mail_conf)
    handle_send(mail_conf, message)


def handle_send(mail_conf, message):
    """Connect to the SMTP server and send the message

    :param mail_conf: MailConfig object
    :param message: MIMEText object
    """
    if mail_conf.encrypt == 'no':
        server = smtplib.SMTP(mail_conf.server, mail_conf.port)
    elif mail_conf.encrypt == 'tls':
        server = smtplib.SMTP(mail_conf.server, mail_conf.port)
        server.starttls()
    elif mail_conf.encrypt == 'ssl':
        server = smtplib.SMTP_SSL(mail_conf.server)
    else:
        raise AntismashRunError('Invalid email encryption configuration')

    if mail_conf.encrypt != 'no' and mail_conf.username != '' and mail_conf.password != '':
        server.login(mail_conf.username, mail_conf.password)

    server.send_message(message)
    server.quit()

