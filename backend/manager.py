""" Module to handle our migrations """

from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand

from backend.app import app, db


migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()
