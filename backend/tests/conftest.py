""" Module that defines fixtures to all tests."""
import pytest

from flask_mail import Message

from backend.models import Usuario


@pytest.fixture
def valid_usuario():
    """ Returns a valid Usuario """
    usuario = Usuario('123456789', '', '', '', '', '', '')
    usuario.id = 5

    return usuario


@pytest.fixture
def valid_msg():
    """ Returns a valid flask_mail.Message """
    return Message('Subject', sender='sender@clozer.com.br',
                   recipients=['test@clozer.com.br'], body='Body')

