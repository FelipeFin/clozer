from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text

from backend.app import db


class DAO(object):
    """
    Data Access Object class that will provide the basic
    CRUD operations.
    All models will inherit this class.
    """
    @classmethod
    def get_all(cls, parsed=False):
        """
        Gets all results from the database

        Args:
            cls (class): the class object
            parsed (bool): call to_json on the retrieved data

        Returns:
            (list): Data result from database
        """
        data = db.session.query(cls).all()
        if parsed:
            data = [d.to_json() for d in data]

        return data

    @classmethod
    def get_first(cls, **kwargs):
        """
        Return the first result matching the query passed on kwargs

        Args:
            cls (class): the class object
            kwargs (dict): containing the filter_by args

        Returns:
            (class): Data result from database
        """
        return db.session.query(cls).filter_by(**kwargs).first()

    @classmethod
    def update_or_insert(cls, obj):
        """
        Updates or Inserts the obj in the database

        Args:
            cls (class): the class object
            obj (object): object that will be updated/inserted
        """
        db.session.add(obj)
        db.session.commit()

    @classmethod
    def delete(cls, obj):
        """
        Deletes the obj in the database

        Args:
            cls (class): the class object
            obj (object): object that will be updated/inserted
        """
        db.session.delete(obj)
        db.session.commit()


class Contato(db.Model, DAO):
    __tablename__ = 'contato'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String())
    contato = db.Column(db.String())
    texto = db.Column(db.String())
    timestamp = db.Column(db.DateTime(), default=datetime.now)

    def __init(self, nome, contato, texto):
        print (1, 'init')
        self.nome = nome
        self.contato = contato
        self.texto = texto

    def __repr__(self):
        base = '<contato id={}, nome={}, contato={}, text={}>'
        return base.format(self.id, self.nome, self.contato, self.text)

    def to_json(self):
        formato = '%d/%m/%Y %H:%M:%S'
        return {
            'id': self.id, 'nome': self.nome,
            'contato': self.contato, 'texto': self.texto,
            'timestamp': datetime.strftime(self.timestamp, formato)
        }


class Imagem(db.Model, DAO):
    __tablename__ = 'imagem'

    id = db.Column(db.Integer, primary_key=True)
    anuncio_id = db.Column(db.Integer, db.ForeignKey('anuncio.id'))
    titulo = db.Column(db.String())
    img_filename = db.Column(db.String())

    def __repr__(self):
        return '<image id={},titulo={}>'.format(self.id, self.titulo)

    def to_json(self):
        return {
            'id': self.id, 'anuncio_id': self.anuncio_id,
            'imagem': self.img_filename
        }

    @staticmethod
    def add_image(image_dict):
        """
        Adds the image to the database

        Args:
            image_dict (dict): Dict containing the image information
        """
        img_filename = image_dict['img_filename'].replace('static/', '')
        new_image = Imagem(anuncio_id=image_dict['anuncio_id'],
                           img_filename=img_filename)
        db.session.add(new_image)
        db.session.commit()


class Anuncio(db.Model, DAO):
    __tablename__ = 'anuncio'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    usuario = relationship('Usuario', back_populates='anuncios')
    imagens = relationship(Imagem, order_by='Imagem.id')
    titulo = db.Column(db.String)
    descricao = db.Column(db.String)
    valor = db.Column(db.Integer)
    marca = db.Column(db.String)
    modelo = db.Column(db.String)
    ano = db.Column(db.Integer)
    cor = db.Column(db.String)
    # Field to enable faster search
    query_busca = db.Column(db.String)
    aprovado = db.Column(db.Boolean, default=False)
    views = db.Column(db.Integer, default=0)
    troca = db.Column(db.Boolean, default=False)
    leilao = db.Column(db.Boolean, default=False)
    aprovado_em = db.Column(db.DateTime())
    criado_em = db.Column(db.DateTime(), default=datetime.now)
    cidade_veiculo = db.Column(db.String, default='')
    estado_veiculo = db.Column(db.String, default='')

    def __init__(self, usuario_id, titulo, descricao, valor):
        self.usuario_id = usuario_id
        self.titulo = titulo
        self.descricao = descricao
        self.valor = valor

    def __repr__(self):
        base = '<usuario_id {} id {}> {} {}'
        return base.format(self.usuario_id, self.id, self.titulo, str(self.valor))

    def imagens_to_json(self):
        return [img.to_json() for img in self.imagens]

    def to_json(self, include_usuario=True):
        r = {
            'id': self.id,
            'titulo': self.titulo, 'descricao': self.descricao,
            'valor': self.valor, 'marca': self.marca,
            'modelo': self.modelo, 'ano': self.ano,
            'cor': self.cor, 'aprovado': self.aprovado,
            'views': self.views, 'imagens': self.imagens_to_json(),
            'troca': self.troca, 'leilao': self.leilao,
            'cidade_veiculo': self.cidade_veiculo,
            'estado_veiculo': self.estado_veiculo,
            'criado_em': datetime.strftime(self.criado_em, '%d/%m/%Y %H:%M:%S'),
            # 'aprovado_em': datetime.strftime(self.aprovado_em,
            #                                  '%d/%m/%Y %H:%M:%S')
        }
        if include_usuario:
            r['usuario'] = self.usuario.to_json(include_anuncios=False)
        return r

    def criar_query_busca(self):
        return '{} {} {} {}'.format(self.marca, self.modelo, self.ano, self.cor)

    @staticmethod
    def get(order_by, limit):
        order_by = Anuncio.criado_em.desc()
        if order_by == 'random':
            order_by = func.random()
        anuncios = db.session.query(Anuncio).filter_by(aprovado=True)
        if limit:
            anuncios = anuncios.order_by(order_by).limit(limit).all()
        else:
            anuncios = anuncios.order_by(order_by).all()

        return [anuncio.to_json() for anuncio in anuncios]

    @staticmethod
    def buscar(query_usuario, order_by, limit):
        if limit == ' LIMIT None':
            limit = ''
        order_by = ' ORDER BY {}'.format(order_by)
        if order_by == ' ORDER BY None':
            order_by = ''
        query = 'SELECT * FROM anuncio WHERE aprovado=true'
        query += ' AND to_tsvector(query_busca) @@ to_tsquery(\'{}\'){}{};'
        query = query.format(query_usuario, order_by, limit)
        anuncios = [
            a.to_json()
            for a in db.session.query(Anuncio).from_statement(text(query)).all()
        ]
        return anuncios


class Usuario(db.Model, DAO):
    __tablename__ = 'usuario'
    id = db.Column(db.Integer,
                   db.Sequence('seq_usuario_id', start=1, increment=1),
                   primary_key=True, autoincrement=True)
    anuncios = relationship(Anuncio)
    facebook_id = db.Column(db.String, unique=True)
    nome = db.Column(db.String)
    # Pessoa Fisica ou Garagem
    tipo = db.Column(db.String, default='Pessoa Fisica')
    cidade = db.Column(db.String, default='')
    estado = db.Column(db.String, default='')
    telefone = db.Column(db.String, default='')
    email = db.Column(db.String, default='')
    views = db.Column(db.Integer, default=0)
    cadastrado_em = db.Column(db.DateTime(), default=datetime.now)

    def __init__(self, facebook_id, nome, email, tipo, cidade, estado, telefone):
        self.facebook_id = facebook_id
        self.nome = nome
        self.email = email
        self.tipo = tipo
        self.cidade = cidade
        self.estado = estado
        self.telefone = telefone

    def __repr__(self):
        return '<id {}> {} {}'.format(self.id, self.facebook_id, self.nome)

    def get_id(self):
        return self.id

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def to_json(self, include_anuncios=True):
        formato = '%d/%m/%Y %H:%M:%S'
        r = {
            'id': self.id, 'facebook_id': self.facebook_id,
            'nome': self.nome, 'tipo': self.tipo,
            'cidade': self.cidade, 'estado': self.estado,
            'telefone': self.telefone,
            'email': self.email, 'views': self.views,
            'cadastrado_em': datetime.strftime(self.cadastrado_em, formato)
        }
        if include_anuncios:
            anuncios = [a.to_json(include_usuario=False) for a in self.anuncios]
            r['anuncios'] = anuncios

        return r

    @staticmethod
    def get(id):
        usuario = db.session.query(Usuario)
        if len(str(id)) < 6:
            usuario = usuario.filter_by(id=id).first()
        else:
            usuario = usuario.filter_by(facebook_id=id).first()

        return usuario

    @classmethod
    def get_all(cls, parsed=False):
        data = db.session.query(cls).all()
        if parsed:
            data = [d.to_json(False) for d in data]

        return data


class Busca(db.Model, DAO):
    __tablename__ = 'busca'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    usuario = db.Column(db.Integer)
    busca = db.Column(db.String)
    buscado_em = db.Column(db.DateTime(), default=datetime.now)

    def __init__(self, usuario, busca):
        self.usuario = usuario
        self.busca = busca

    def __repr__(self):
        return '{}: {}'.format(self.buscado_em, self.busca)
