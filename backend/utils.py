""" Module for utilitary function """
import re

from flask import current_app as app
from flask_jwt_extended import get_jwt_identity
from flask_restful.reqparse import RequestParser
from requests import post

from backend.app import mail
from backend.config import Config as config


def create_identity(usuario):
    """
    Creates and identify for the user with the format:
    id-facebook_id Eg: 8-123456789

    Args:
        usuario (Usuario): the Usuario object

    Returns:
        (str): the identity for the user
    """
    return '{}-{}'.format(str(usuario.id), usuario.facebook_id)


def get_current_user():
    """
    Gets the current used based on get_jwt_identify

    Returns:
        (dict): Containing the usuario_id and the facebook_id
    """
    identity = get_jwt_identity()
    usuario_id = int(identity.split('-')[0])
    facebook_id = int(identity.split('-')[1])
    return {'id': usuario_id, 'facebook_id': facebook_id}


def send_to_slack(msg):
    """
    Sends a notification to our slack channel

    Args:
        msg (str): message to be sent
    """
    data = {'text': msg}
    url = config.SLACK_HOOK
    post(url, json=data)


def send_email(msg):
    """
    Sends an email and logs it

    Args:
        msg (flask_mail.Message): message object to be sent
    """
    if msg and re.match(r"[^@]+@[^@]+\.[^@]+", msg.sender):
        mail.send(msg)
        log(msg.subject, msg.recipients)


def log(*data):
    """
    Adds data to our logger

    Args:
        *data (tuple): data to be logged
    """
    app.logger.info(str(data))


def get_parser(arg_list):
    """
    Creates a reqparse.RequestParser based on the args supplied

    Args:
        arg_list (list): List containing expected args

    Returns
        (reqparse.RequestParser): with all arguments supplied
    """
    parser = RequestParser()
    args_types = {
        'int': ['valor', 'ano'],
        'str': [
            'email', 'telefone', 'tipo', 'cidade', 'estado',
            'facebook_id', 'nome', 'contato', 'texto', 'titulo', 'descricao', 'marca', 'cor',
            'query', 'limit', 'order_by'
        ]
    }
    for argument in arg_list:
        if argument in args_types['int']:
            _type = int
        elif argument in args_types['str']:
            _type = str
        parser.add_argument(argument, type=_type, required=False)

    return parser
