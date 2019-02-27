""" Module for utilitary function """
import pytest
from mock import patch, Mock, call

from backend import utils
from backend.config import Config as config
from backend.models import Usuario


VALID_IDENTITY = '5-123456789'


def test_create_identity(valid_usuario):
    """Tests create_identity return"""
    expected_identity = VALID_IDENTITY
    _identity = utils.create_identity(valid_usuario)

    assert expected_identity == _identity


@patch('backend.utils.get_jwt_identity')
def test_get_current_user(get_jwt_identity, valid_usuario):
    """Tests get_current_user return"""
    get_jwt_identity.return_value = VALID_IDENTITY
    current_user = utils.get_current_user()

    assert current_user['id'] == valid_usuario.id
    assert current_user['facebook_id'] == int(valid_usuario.facebook_id)


@patch('backend.utils.post')
def test_send_to_slack(post):
    """Tests if send_to_slack calls the post function """
    msg = 'Message'
    data = {'text': msg}
    url = config.SLACK_HOOK
    utils.send_to_slack(msg)

    post.assert_called_once_with(url, json=data)


@patch('backend.utils.log')
@patch('backend.utils.mail')
def test_send_email_with_valid_message(mail, log, valid_msg):
    """Tests send_email with valid message """
    utils.send_email(valid_msg)
    mail.send.assert_called_once_with(valid_msg)
    log.assert_called_once_with(valid_msg.subject, valid_msg.recipients)


@patch('backend.utils.log')
@patch('backend.utils.mail')
def test_send_email_with_empty_message(mail, log):
    """Tests send_email with empty message """
    utils.send_email({})
    mail.send.assert_not_called()
    log.assert_not_called()


@patch('backend.utils.app')
def test_log(app):
    """Tests if test_log calls the info method """
    utils.log('Testing')
    app.logger.info.assert_called_once()
