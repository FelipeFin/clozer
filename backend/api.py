""" Module that handles all API endpoints """

import locale
import os
import shutil

from io import BytesIO
from PIL import Image

from flask import render_template, Blueprint
from flask_restful import Resource, abort
from flask_mail import Message
from flask_jwt_extended import (create_access_token, create_refresh_token,
                                jwt_required, jwt_refresh_token_required,
                                get_jwt_identity)
from werkzeug import FileStorage, exceptions

from backend.config import Config as config
from backend.app import db
from backend.models import Usuario, Anuncio, Imagem, Contato, Busca

from backend.utils import (
    get_parser, get_current_user, create_identity, send_to_slack, send_email,
    log
)

api_bp = Blueprint('api', __name__)


ANUNCIO_ARGS_LIST = [
    'titulo', 'descricao', 'valor', 'cidade_veiculo', 'estado_veiculo',
    'troca', 'leilao', 'marca', 'modelo', 'cor', 'ano'
]
ANUNCIOS_ARGS_LIST = ['limit', 'order_by']
BUSCA_ARGS_LIST = ['query', 'limit', 'order_by']
CONTATO_ARGS_LIST = ['nome', 'contato', 'texto']
USUARIO_ARGS_LIST = [
    'facebook_id', 'nome', 'email', 'tipo', 'cidade', 'estado', 'telefone'
]
LOGIN_ARGS_LIST = ['facebook_id']


class CustomException(exceptions.HTTPException):
    """
    Exception class that inhereits from exceptions.HTTPException
    and can be customized with the code and description
    """
    code = 402
    description = 'Limite de Anuncios excedido!'


class ContatosResource(Resource):
    """
    Resource that handles the Contato listing
    """
    def get(self):
        """
        List all Contato

        Returns:
            (dict): Containing all Contatos as JSON
        """
        return Contato.get_all(parsed=True)


class ContatoResource(Resource):
    """
    Resource that handles all interactions in the session Contato
    """
    def get(self, id):
        """
        Gets the Contato with the supplied id

        Args:
            id (int): The id of the Contato

        Returns:
            (dict): Containing the Contato as JSON

        Raises:
            (HTTPException): if the Contato does not exist
        """
        contato = Contato.get_first(id=id)
        if not contato:
            abort(404, erro="Contato {} nao existe".format(id))

        return {'contato': contato.to_json()}

    def post(self):
        """
        Saves the Contato with the supplied arguments,
        sends an email informing the user about it and
        sends a Slack Notification to us

        Returns:
            (dict): Containing the inserted Contato as JSON
        """
        parser = get_parser(CONTATO_ARGS_LIST)
        args = parser.parse_args()
        contato = Contato(nome=args['nome'],
                          contato=args['contato'],
                          texto=args['texto'])
        Contato.update_or_insert(contato)

        # Send email notification
        if config.ENVIAR_EMAILS:
            body = 'Mensagem salva com sucesso:\n' + args['texto']
            msg = Message('Mensagem cadastrada com sucesso!',
                          sender='atendimento@clozer.com.br',
                          recipients=[args['contato']],
                          body=body)
            send_email(msg)

        # Slack Notification
        try:
            msg = 'CONTATO({}) > {} - {}: {}'.format(
                contato.id, args['nome'], args['contato'], args['texto']
            )
            send_to_slack(msg)
            log('ContatoResouce POST', contato)
        except Exception as e:
            log('ContatoResource Exception:', e)

        return {contato.id: contato.to_json()}


class AnunciosResource(Resource):
    """
    Resource that handles the Anuncio listing
    """
    def get(self):
        """
        Lit all Anuncios.
        It can receive limit and order_by as GET params

        Returns:
            (dict): Dict containing all Anuncios as JSON
        """
        parser = get_parser(ANUNCIOS_ARGS_LIST)
        args = parser.parse_args()
        anuncios = Anuncio.get(args['order_by'], args['limit'])

        return {'anuncios': anuncios}


class AnuncioResource(Resource):
    """
    Resource that handles actions for individual Anuncio
    """
    def get(self, id):
        """
        Gets the Anuncio with the supplied id

        Args:
            id (int): The id of the Anuncio

        Returns:
            (dict): Containing the Anuncio as JSON

        Raises:
            (HTTPException): if the Anuncio does not exist
        """
        anuncio = Anuncio.get_first(id=id)
        if not anuncio:
            abort(404, erro="Anuncio de id {} nao existe".format(id))
        anuncio.views = anuncio.views + 1
        Anuncio.update_or_insert(anuncio)

        return {'anuncio': anuncio.to_json()}

    @jwt_required
    def post(self):
        """
        Saves the Anuncio with the supplied arguments,
        sends an email informing the user about it and
        sends a Slack Notification to us

        Returns:
            (dict): Containing the inserted Anuncio as JSON

        Raises:
            (CustomException): If the user exceeded the max number of Anuncio
        """
        parser = get_parser(ANUNCIO_ARGS_LIST)
        parser.add_argument('imagens', required=False, location='files',
                            type=FileStorage, action='append')
        args = parser.parse_args()
        usuario_logado_id = get_current_user()['id']
        usuario = Usuario.get_first(id=usuario_logado_id)
        if usuario and len(usuario.anuncios) >= config.LIMITE_ANUNCIOS_FREE:
            raise CustomException
        anuncio = Anuncio(usuario_logado_id, '', '', 0)
        for arg_name, arg_value in args.items():
            if arg_name == 'imagens':
                continue
            if arg_value:
                if arg_name in ['troca', 'leilao']:
                    setattr(anuncio, arg_name, bool(arg_value))
                else:
                    setattr(anuncio, arg_name, arg_value)
        Anuncio.update_or_insert(anuncio)

        # Add images
        imagens = args['imagens']
        if imagens:
            upload_images(anuncio, imagens)

        # Send Email Notification
        if config.ENVIAR_EMAILS:
            locale.setlocale(locale.LC_ALL, '')
            anuncio.valor_formatado = locale.currency(anuncio.valor)
            html = render_template('anuncio-recebido.html', anuncio=anuncio)
            msg = Message('Anuncio cadastrado com sucesso!',
                          sender='atendimento@clozer.com.br',
                          recipients=[usuario.email],
                          html=html)
            send_email(msg)

        # Slack Notification
        try:
            msg = 'Anuncio({}) > {}({}): {} R${}'.format(
                anuncio.id, usuario.nome, usuario.id,
                anuncio.titulo.encode('utf-8'), str(anuncio.valor)
            )
            send_to_slack(msg)
        except Exception as e:
            log('Anuncio Exception', e)
        log('Anuncio POST', anuncio)

        return {anuncio.id: anuncio.to_json()}

    @jwt_required
    def put(self, id):
        """
        Updates the Anuncio with the supplied arguments and
        sends a Slack Notification to us

        Args:
            id (int): The id of the Anuncio

        Returns:
            (dict): Containing the updated Anuncio as JSON

        Raises:
            (HTTPException): If the user tries to update an inexistent Anuncio
                             If the user tries to update an Anuncio from other
        """
        parser = get_parser(ANUNCIO_ARGS_LIST)
        args = parser.parse_args()
        usuario_logado_id = get_current_user()['id']
        anuncio = Anuncio.get_first(id=id)

        if not anuncio:
            abort(404, erro='Anuncio de id {} nao existe'.format(id))
        if anuncio.usuario_id != usuario_logado_id:
            abort(404, erro='Criador do anuncio nao eh este usuario')

        args = parser.parse_args()
        for arg_name, arg_value in args.items():
            print(1, arg_name, 2, arg_value)
            if arg_value:
                if arg_name in ['troca', 'leilao']:
                    setattr(anuncio, arg_name, bool(arg_value))
                else:
                    setattr(anuncio, arg_name, arg_value)
        anuncio.aprovado = False
        Anuncio.update_or_insert(anuncio)
        log('Anuncio PUT', anuncio)

        return {anuncio.id: anuncio.to_json()}

    @jwt_required
    def delete(self, id):
        """
        Removes the Anuncio with the supplied id and all its images.
        Algo sends a Slack Notification to us

        Args:
            id (int): The id of the Anuncio that will be deleted

        Returns:
            (dict): Empty dict

        Raises:
            (HTTPException): If the user tries to remove an inexistent Anuncio
                             If the user tries to remove an Anuncio from other
        """
        usuario_logado_id = get_current_user()['id']
        anuncio = Anuncio.get_first(id=id)
        if not anuncio:
            abort(404, erro='Anuncio de id {} nao existe'.format(id))
        if anuncio.usuario_id != usuario_logado_id:
            abort(404, erro='Criador do anuncio nao eh este usuario')
        # Deleting images
        for imagem in anuncio.imagens:
            Imagem.delete(imagem)
        path_usuario = '{}/{}'.format(config.IMAGE_DIR, usuario_logado_id)
        path_anuncio = '{}/{}'.format(path_usuario, anuncio.id)
        shutil.rmtree(path_anuncio)
        log('Anuncio DELETE', anuncio)
        Anuncio.delete(anuncio)

        return {}


class UsuariosResource(Resource):
    """
    Resource that handles the Usuario listing

    Returns:
        (dict): Containing all Usuarios as JSON
    """
    def get(self):
        """
        Lit all Usuarios.

        Returns:
            (dict): Dict containing all usuarios as JSON
        """
        usuarios = Usuario.get_all(parsed=True)
        return {'usuarios': usuarios}


class UsuarioResource(Resource):
    """
    Resource that handles actions for individual Usuarios
    """
    def get(self, id):
        """
        Gets the Usuario with the supplied id and
        increments its views

        Args:
            id (int): The id of the Usuario

        Returns:
            (dict): Containing the Usuario as JSON

        Raises:
            (HTTPException): if the Usuario does not exist
        """
        usuario = Usuario.get(id)
        if not usuario:
            abort(404, erro="Usuario {} nao existe".format(id))
        usuario.views = usuario.views + 1
        Usuario.update_or_insert(usuario)

        return {'usuario': usuario.to_json()}

    def post(self):
        """
        Saves the Usuario with the supplied arguments,
        sends a welcome email the user and
        sends a Slack Notification to us

        Returns:
            (dict): Containing the inserted Anuncio as JSON

        Raises:
            (HTTPException): If the user with the facebook_id already exists
        """
        parser = get_parser(USUARIO_ARGS_LIST)
        args = parser.parse_args()
        usuario = Usuario.get_first(facebook_id=args['facebook_id'])
        if usuario:
            error_msg = 'Usuario {} ja existe. Id {}'
            abort(404, erro=error_msg.format(args['facebook_id'], usuario.id))

        usuario = Usuario(
            facebook_id=args['facebook_id'], nome=args['nome'],
            email=args['email'], tipo=args['tipo'],
            cidade=args['cidade'], estado=args['estado'],
            telefone=args['telefone']
        )
        Usuario.update_or_insert(usuario)

        # Email Notification
        if config.ENVIAR_EMAILS:
            if args['email']:
                html = render_template('bem-vindo.html')
                msg = Message('Bem vindo ao Clozer!',
                              sender='atendimento@clozer.com.br',
                              recipients=[args['email']],
                              html=html)
                send_email(msg)

        # Slack Notification
        try:
            base_msg = 'Usuario({}) > {}: {}, {}, {}-{}'
            msg = base_msg.format(
                usuario.id, usuario.nome, usuario.email,
                usuario.telefone, usuario.cidade.encode('utf-8'), usuario.estado
            )
            send_to_slack(msg)
        except Exception as e:
            log('Exception Usuario POST', e)
        log('Usuario POST', usuario)

        return {usuario.id: usuario.to_json()}

    @jwt_required
    def put(self, id):
        """
        Updates the Usuario with the supplied arguments and
        sends a Slack Notification to us

        Args:
            id (int): The id of the Usuario

        Returns:
            (dict): Containing the updated Usuario as JSON

        Raises:
            (HTTPException): If the user tries to update an inexistent Usuario
                             If the user tries to update another user
        """
        parser = get_parser(USUARIO_ARGS_LIST)
        usuario = Usuario.get_first(id=id)
        usuario_logado_id = get_current_user()['id']
        if not usuario:
            abort(404, erro="Usuario de id {} nao existe".format(id))
        if usuario.id != usuario_logado_id:
            abort(404, erro="Usuario nao pode alterar dados de outro usuario")
        args = parser.parse_args()
        for arg_name, arg_value in args.items():
            if arg_value:
                setattr(usuario, arg_name, arg_value)

        Usuario.update_or_insert(usuario)
        log('Usuario PUT', usuario)

        return {usuario.id: usuario.to_json()}


class LoginResource(Resource):
    """
    Resource that handles our login
    """
    def post(self):
        """
        Logs the user in our system and
        sends a Slack Notification to us

        Returns:
            (dict): Containing the usuario_id, access_token and refresh_token

        Raises:
            (HTTPException): If the user does not inform its facebook_id
                             If the user with the supplied facebook_id does not exist
        """
        parser = get_parser(LOGIN_ARGS_LIST)
        args = parser.parse_args()
        if not args['facebook_id']:
            error_msg = 'Informe o facebook_id do usuario'
            abort(404, erro=error_msg)
        usuario = Usuario.get_first(facebook_id=args['facebook_id'])
        if not usuario:
            error_msg = 'Usuario com facebook_id nao existe'
            abort(404, erro=error_msg.format(args['facebook_id']))

        identity = create_identity(usuario)
        access_token = create_access_token(identity=identity)
        refresh_token = create_refresh_token(identity=identity)
        log('Login:', usuario)
        return {
            'usuario_id': usuario.id,
            'access_token': access_token,
            'refresh_token': refresh_token
        }


class ImagemResource(Resource):
    """
    Resource that handles the retrieval and deletion of Images
    """
    def get(self, id):
        """
        Gets the Imagem with the supplied id

        Args:
            id (int): The id of the Image

        Returns:
            (dict): Containing the Imagem as JSON

        Raises:
            (HTTPException): if the Imagem does not exist
        """
        imagem = Imagem.get_first(id=id)
        if not imagem:
            abort(404, erro="Imagem de id {} nao existe".format(id))
        return {'imagem': imagem.to_json()}

    @jwt_required
    def delete(self, anuncio_id, id):
        """
        Removes the Anuncio with the supplied id and all its images.
        Algo sends a Slack Notification to us

        Args:
            anuncio_id (int): The id of the Anuncio
            id (int): The id of the Image that will be deleted

        Returns:
            (dict): Empty dict

        Raises:
            (HTTPException): If the user tries to remove an image from an inexistent Anuncio
                             If the user tries to remove an Imagem from other user
        """
        usuario_logado_id = get_current_user()['id']
        anuncio = Anuncio.get_first(id=anuncio_id)
        if not anuncio:
            abort(404, erro='Anuncio de id {} nao existe'.format(id))
        if anuncio.usuario_id != usuario_logado_id:
            abort(404, erro='Criador do anuncio nao eh este usuario')
        imagem = db.session.query(Imagem).filter_by(id=id).first()
        Imagem.delete(imagem)
        log('Imagem DELETE', imagem)

        return {}


class BuscaResource(Resource):
    """
    Resource that handles our search
    """
    def get(self):
        """
        Performs a text search on our Anuncios and saves the query searched.
        It can receive limit and order_by as GET params.

        Returns:
            (dict): Containing approved Anuncios that matched the search
        """
        parser = get_parser(BUSCA_ARGS_LIST)
        args = parser.parse_args()
        query_usuario = args['query'].strip().replace(' ', ' & ')
        limit = ' LIMIT {}'.format(args['limit'])
        anuncios = Anuncio.buscar(query_usuario, args['order_by'], limit)
        # TODO: Find a way to get the usuario_logado_id
        usuario_logado_id = 0
        # Saving the search
        busca = Busca(usuario_logado_id, query_usuario)
        Busca.update_or_insert(busca)
        log('Busca', busca)

        return {'anuncios': anuncios}


def upload_images(anuncio, imagens):
    """
    Auxiliary function that creates all necessary directories and
    uploads images for the Anuncio.

    Args:
        anuncio (Anuncio): the Anuncio object
        imagens (list): List of images o be inserted
    """
    usuario_id = anuncio.usuario_id
    anuncio_id = anuncio.id
    size = config.IMAGE_WIDTH, config.IMAGE_HEIGHT
    path_usuario = '{}/{}'.format(config.IMAGE_DIR, usuario_id)
    path_anuncio = '{}/{}'.format(path_usuario, anuncio_id)
    # Creating the user file directory
    if not os.path.exists(path_usuario):
        os.makedirs(path_usuario)
        os.makedirs(path_anuncio)
    # Creating the anuncio file directory
    if not os.path.exists(path_anuncio):
        os.makedirs(path_anuncio)

    for index, file in enumerate(imagens):
        img = Image.open(BytesIO(file.read()))
        # Resizing
        wpercent = (config.IMAGE_WIDTH / float(img.size[0]))
        height = int((float(img.size[1]) * float(wpercent)))
        size = config.IMAGE_WIDTH, height
        img = img.resize(size, Image.ANTIALIAS)
        full_path = '{}/{}.jpg'.format(path_anuncio, 'imagem' + str(index))
        quality_val = 90
        img.convert('RGB').save(full_path, 'JPEG', quality=quality_val)
        # Saving to database
        Imagem.add_image({
            'anuncio_id': anuncio_id,
            'img_filename': full_path
        })
    log('upload_images', anuncio_id, full_path)


class TokenRefreshResource(Resource):
    """
    Resouce that handles the Token Refresh functionality
    """
    @jwt_refresh_token_required
    def post(self):
        """
        Create a new access_token based on the current_user

        Returns:
            (dict): Containing the new access_token
        """
        current_user = get_jwt_identity()
        access_token = create_access_token(identity=current_user)
        log('token refresh', current_user)

        return {'access_token': access_token}
