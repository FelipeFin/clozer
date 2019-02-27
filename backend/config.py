class BaseConfig(object):
    # Password
    SECRET_KEY = 'password'
    JWT_SECRET_KEY = 'jwt-secret-string'

    FACEBOOK_APP_ID = ''
    FACEBOOK_APP_SECRET = ''

    # Images data
    IMAGE_DIR = 'static/images'
    IMAGE_WIDTH = 1024
    IMAGE_HEIGHT = 768

    # Zoho mail configuration
    MAIL_SERVER = 'smtp.zoho.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = 'email'
    MAIL_PASSWORD = 'password'

    # Sentry information
    SENTRY_DSN = ''

    # Slack information
    SLACK_HOOK = ''

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    API_VERSION = '/api/v1/'


class Config(BaseConfig):
    """Production configuration."""
    # App config
    LIMITE_ANUNCIOS_FREE = 500
    ENVIAR_EMAILS = False
    ERROR_404_HELP = False
    DEBUG = False

    # TODO: Move sensitive data to env vars

    # Postgres data
    POSTGRES = {
        'user': 'postgres',
        'pw': 'password',
        'db': 'clozer_db2',
        'host': 'localhost',
        'port': '5432',
    }
    POSTGRES_URI = 'postgresql://%(user)s:%(pw)s@%(host)s:%(port)s/%(db)s' % POSTGRES
    SQLALCHEMY_DATABASE_URI = POSTGRES_URI


class TestConfig(BaseConfig):
    """Test configuration."""
    TESTING = True
    DEBUG = True

    # Postgres data
    POSTGRES = {
        'user': 'postgres',
        'pw': 'password',
        'db': 'clozer_db_testing',
        'host': 'localhost',
        'port': '5432',
    }
    POSTGRES_URI = 'postgresql://%(user)s:%(pw)s@%(host)s:%(port)s/%(db)s' % POSTGRES
    SQLALCHEMY_DATABASE_URI = POSTGRES_URI
