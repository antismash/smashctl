"""Tests for the email sending"""
from antismash_models import SyncJob as Job
from argparse import Namespace
from email.mime.text import MIMEText
import smtplib
import pytest

from smashctl import mail


def generate_mail_conf():
    args = Namespace(
        base_url='https://example.org',
        encrypt='ssl',
        password='secret',
        port=587,
        sender='alice@example.org',
        server='mail.example.com',
        support='bob@example.org',
        tool='antiSMASH',
        username='alice'
    )
    return mail.MailConfig.from_args(args)


def test_MailConfig():
    args = Namespace(server='')

    mail_config = mail.MailConfig.from_args(args)
    assert not mail_config.configured

    mail_config = generate_mail_conf()
    assert mail_config.configured


def test_send_mail(mocker):
    mock_handle_send = mocker.patch('smashctl.mail.handle_send')
    job = Job(None, 'bacteria-fake')
    job.state = 'done'
    job.email = 'claire@example.com'

    conf = generate_mail_conf()
    mail.send_mail(conf, job)
    message = mock_handle_send.call_args[0][1]
    assert message['From'] == conf.sender
    assert message['To'] == job.email
    text = message.get_payload()
    assert 'The antiSMASH job' in text
    assert 'You can find the results' in text
    mock_handle_send.reset()

    job.state = 'failed'
    mail.send_mail(conf, job)
    message = mock_handle_send.call_args[0][1]
    assert message['From'] == conf.sender
    assert message['To'] == job.email
    text = message.get_payload()
    assert 'The antiSMASH job' in text
    assert 'Please contact' in text


def test_handle_send_plain(mocker):
    mock_server = mocker.MagicMock(spec=smtplib.SMTP, instance=True)
    mock_smtp = mocker.patch('smtplib.SMTP', autospec=True, return_value=mock_server)

    conf = generate_mail_conf()
    conf.encrypt = 'no'

    message = MIMEText('This is a test')
    message['From'] = conf.sender
    message['To'] = 'claire@example.com'

    mail.handle_send(conf, message)
    mock_smtp.assert_called_once_with(conf.server, conf.port)
    mock_server.send_message.assert_called_once_with(message)
    mock_server.quit.assert_called_once_with()


def test_handle_send_ssl(mocker):
    mock_server = mocker.MagicMock(spec=smtplib.SMTP, instance=True)
    mock_smtp_ssl = mocker.patch('smtplib.SMTP_SSL', autospec=True, return_value=mock_server)

    conf = generate_mail_conf()

    message = MIMEText('This is a test')
    message['From'] = conf.sender
    message['To'] = 'claire@example.com'

    mail.handle_send(conf, message)
    mock_smtp_ssl.assert_called_once_with(conf.server)
    mock_server.send_message.assert_called_once_with(message)
    mock_server.quit.assert_called_once_with()


def test_handle_send_tls(mocker):
    mock_server = mocker.MagicMock(spec=smtplib.SMTP, instance=True)
    mock_smtp = mocker.patch('smtplib.SMTP', autospec=True, return_value=mock_server)

    conf = generate_mail_conf()
    conf.encrypt = 'tls'

    message = MIMEText('This is a test')
    message['From'] = conf.sender
    message['To'] = 'claire@example.com'

    mail.handle_send(conf, message)
    mock_smtp.assert_called_once_with(conf.server, conf.port)
    mock_server.send_message.assert_called_once_with(message)
    mock_server.quit.assert_called_once_with()


def test_handle_send_invalid(mocker):
    mock_server = mocker.MagicMock(spec=smtplib.SMTP, instance=True)
    mocker.patch('smtplib.SMTP', autospec=True, return_value=mock_server)

    conf = generate_mail_conf()
    conf.encrypt = 'foo'

    message = MIMEText('This is a test')
    message['From'] = conf.sender
    message['To'] = 'claire@example.com'
    with pytest.raises(mail.AntismashRunError):
        mail.handle_send(conf, message)