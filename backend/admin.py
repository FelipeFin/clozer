""" Module that handles the admin area """

import datetime
import os

from flask import (
    render_template, request, flash, redirect, url_for, Blueprint
)
from flask_mail import Message

from backend.app import db
from backend.config import Config as config
from backend.models import Usuario, Anuncio, Imagem, Busca
from backend.utils import send_email

admin_bp = Blueprint('admin', __name__, template_folder='templates/admin')
data = {}


def _deletar_imagens(anuncio):
    """
    Removes all the images from the specific anuncio.
    It also deletes the directory

    Args:
        anuncio (Anuncio): the Anuncio that the images will be deleted
    """
    if anuncio.imagens:
        for imagem in anuncio.imagens:
            if os.path.exists('static/' + imagem.img_filename):
                # Removing images
                os.unlink('static/' + imagem.img_filename)
            db.session.delete(imagem)
    path_to_remove = '{}/{}/{}'.format(config.IMAGE_DIR, anuncio.usuario_id,
                                       anuncio.id)
    # Removing drectory
    if os.path.exists(path_to_remove):
        os.rmdir(path_to_remove)


@admin_bp.route(config.API_VERSION + 'admin')
def index():
    """
    Main view for the admin area.
    """
    data['usuarios'] = db.session.query(Usuario).order_by('id')
    for usuario in data['usuarios']:
        usuario.qtd_anuncios = len(usuario.anuncios)
    order_by = Anuncio.criado_em.desc()
    data['anuncios'] = db.session.query(Anuncio).order_by(order_by)
    data['buscas'] = db.session.query(Busca)

    return render_template('admin.html', data=data)


@admin_bp.route(config.API_VERSION + 'admin/deletar_anuncio')
def deletar_anuncio():
    """
    View that deletes the Anuncio
    """
    anuncio_id = request.values.get('anuncio_id')
    anuncio = db.session.query(Anuncio).filter_by(id=anuncio_id).first()
    # Removing images
    _deletar_imagens(anuncio)
    db.session.delete(anuncio)
    db.session.commit()
    flash('Anuncio {} deletado com sucesso'.format(anuncio_id))

    return redirect(url_for('admin.index'))


@admin_bp.route(config.API_VERSION + 'admin/aprovar_reprovar_anuncio',
                methods=['GET', 'POST'])
def aprovar_reprovar_anuncio():
    """
    View that approve/reprove the Anuncio.
    If the conf.ENVIAR_EMAILS is True, it will send an email
    to the user informing the status of the approval/reproval.
    """
    anuncio_id = request.values.get('anuncio_id')
    anuncio = db.session.query(Anuncio).filter_by(id=anuncio_id).first()
    aprovar_reprovar = request.values.get('aprovar_reprovar')
    anuncio.aprovado = True if aprovar_reprovar == 'aprovar' else False
    anuncio.aprovado_em = datetime.datetime.now()
    db.session.add(anuncio)
    db.session.commit()

    # Send the approval/reproval email to the user
    if config.ENVIAR_EMAILS:
        if anuncio.aprovado is True:
            titulo = 'Anuncio Aprovado'
            html = render_template('anuncio-aprovado.html', anuncio=anuncio)
        else:
            titulo = 'Anuncio Reprovado'
            html = 'Seu anuncio\nfoi\nreprovado'
        msg = Message(titulo,
                      sender='atendimento@clozer.com.br',
                      recipients=[anuncio.usuario.email],
                      html=html)
        send_email(msg)
    flash('{} de id {} com sucesso'.format(titulo, anuncio_id))

    return redirect(url_for('admin.index'))


@admin_bp.route(config.API_VERSION + 'admin/editar_anuncio',
                methods=['GET', 'POST'])
def editar_anuncio():
    """
    View that edits the Anuncio
    """
    anuncio_id = request.values.get('anuncio_id')
    anuncio = db.session.query(Anuncio).filter_by(id=anuncio_id).first()
    for key, val in request.values.items():
        setattr(anuncio, key, val)
    anuncio.troca = True if request.values.get('troca', False) else False
    anuncio.query_busca = anuncio.criar_query_busca()
    db.session.add(anuncio)
    db.session.commit()
    flash('Anuncio {} editado com sucesso'.format(anuncio_id))

    return redirect(url_for('admin.index'))


@admin_bp.route(config.API_VERSION + 'admin/deletar_usuario')
def deletar_usuario():
    """
    View that deletes the user
    """
    usuario_id = request.values.get('usuario_id')
    usuario = db.session.query(Usuario).filter_by(id=usuario_id).first()
    anuncios = db.session.query(Anuncio).filter_by(usuario_id=usuario.id)
    anuncios_id = [anuncio.id for anuncio in anuncios]
    _filter = Imagem.anuncio_id.in_(anuncios_id)
    imagens = db.session.query(Imagem).filter(_filter)
    # Removing images - bulk dlete
    imagens.delete(synchronize_session=False)
    # Removing anuncios - bulk delete
    anuncios.delete(synchronize_session=False)
    db.session.delete(usuario)
    db.session.commit()
    flash('Usuario {} deletado com sucesso.'.format(usuario_id))

    return redirect(url_for('admin.index'))


@admin_bp.route(config.API_VERSION + 'admin/editar_usuario',
                methods=['GET', 'POST'])
def editar_usuario():
    """
    View that edits the Anuncio
    """
    usuario_id = request.values.get('usuario_id')
    usuario = db.session.query(Usuario).filter_by(id=usuario_id).first()
    for key, val in request.values.items():
        setattr(usuario, key, val)
    db.session.add(usuario)
    db.session.commit()
    flash('Usuario {} editado com sucesso'.format(usuario_id))

    return redirect(url_for('admin.index'))


@admin_bp.route(config.API_VERSION + 'admin/atualizar_query_busca')
def atualizar_query_busca():
    """
    View that updates the query_busca to facilitate the Anuncio search
    """
    anuncios = db.session.query(Anuncio).all()
    for anuncio in anuncios:
        anuncio.query_busca = anuncio.criar_query_busca()
        db.session.add(anuncio)
    db.session.commit()
    flash('Querys busca atualizadas com sucesso')

    return redirect(url_for('admin.index'))
