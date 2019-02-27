from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy

from backend.config import Config
import sentry_sdk


db = SQLAlchemy()
mail = Mail()


def create_app(config_class=Config):
    """
    Creates the Flask application

    Args:
        config_class (object): Config object

    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initilization
    db.init_app(app)
    jwt = JWTManager(app)
    mail.init_app(app)
    sentry_sdk.init(config_class.SENTRY_DSN)
    CORS(app)

    # Admin Blueprint
    from backend.admin import admin_bp
    app.register_blueprint(admin_bp)

    # API Blueprint
    from backend.api import api_bp
    api = Api(api_bp)
    add_api_resources(api)
    app.register_blueprint(api_bp)

    return app


def add_api_resources(api):
    """
    Adds the resources to the API

    Args:
        api (flask_restful.Api): the API to add the resources
    """
    from backend.api import (
        ContatoResource, ContatosResource, UsuarioResource, UsuariosResource,
        AnuncioResource, AnunciosResource, LoginResource, TokenRefreshResource,
        BuscaResource
    )
    api.add_resource(ContatoResource, '/api/v1/contato',
                                      '/api/v1/contato/<string:id>')
    api.add_resource(ContatosResource, '/api/v1/contatos')
    api.add_resource(UsuarioResource, '/api/v1/usuario',
                                      '/api/v1/usuario/<string:id>')
    api.add_resource(UsuariosResource, '/api/v1/usuarios')
    api.add_resource(AnunciosResource, '/api/v1/anuncios')
    api.add_resource(AnuncioResource, '/api/v1/anuncio',
                                      '/api/v1/anuncio/<int:id>')
    api.add_resource(BuscaResource, '/api/v1/busca')
    api.add_resource(LoginResource, '/api/v1/login')
    api.add_resource(TokenRefreshResource, '/api/v1/refresh_token')
