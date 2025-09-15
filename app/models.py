# app/models.py

from . import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone

class Plan(db.Model):
    __tablename__ = 'planes'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    precio = db.Column(db.Integer, nullable=False)
    puede_crear_puestos = db.Column(db.Boolean, default=False, nullable=False)
    organizaciones = db.relationship('Organizacion', back_populates='plan', lazy='dynamic')

class Organizacion(db.Model):
    __tablename__ = 'organizaciones'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('planes.id'), nullable=False)
    plan = db.relationship('Plan', back_populates='organizaciones')
    usuarios = db.relationship('Usuario', back_populates='organizacion', lazy='dynamic')

class Rol(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(64), unique=True, nullable=False)
    usuarios = db.relationship('Usuario', back_populates='rol', lazy='dynamic')

class Barrio(db.Model):
    __tablename__ = 'barrios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    zona = db.Column(db.String(50), nullable=True)
    puestos = db.relationship('Puesto', back_populates='barrio', lazy='dynamic', cascade="all, delete-orphan")
    admins = db.relationship('Usuario', back_populates='barrio_admin', lazy='dynamic')

class Puesto(db.Model):
    __tablename__ = 'puestos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    barrio_id = db.Column(db.Integer, db.ForeignKey('barrios.id'), nullable=False)
    barrio = db.relationship('Barrio', back_populates='puestos')
    actas = db.relationship('Acta', back_populates='puesto', lazy='dynamic', cascade="all, delete-orphan")
    permisos = db.relationship('PermisoPuesto', back_populates='puesto', cascade="all, delete-orphan")

class PermisoPuesto(db.Model):
    __tablename__ = 'permisos'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    puesto_id = db.Column(db.Integer, db.ForeignKey('puestos.id'), nullable=False)
    puede_ver = db.Column(db.Boolean, default=True, nullable=False)
    puede_editar = db.Column(db.Boolean, default=False, nullable=False)
    usuario = db.relationship('Usuario', back_populates='permisos')
    puesto = db.relationship('Puesto', back_populates='permisos')
    __table_args__ = (db.UniqueConstraint('usuario_id', 'puesto_id', name='_usuario_puesto_uc'),)

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    dni = db.Column(db.String(15), unique=True, nullable=False, index=True)
    nombre_completo = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(256))
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    organizacion_id = db.Column(db.Integer, db.ForeignKey('organizaciones.id'), nullable=False)
    barrio_admin_id = db.Column(db.Integer, db.ForeignKey('barrios.id'), nullable=True)
    rol = db.relationship('Rol', back_populates='usuarios')
    organizacion = db.relationship('Organizacion', back_populates='usuarios')
    barrio_admin = db.relationship('Barrio', back_populates='admins')
    actas = db.relationship('Acta', backref='autor', lazy='dynamic')
    permisos = db.relationship('PermisoPuesto', back_populates='usuario', cascade="all, delete-orphan")

    @property
    def password(self):
        raise AttributeError('password no es un atributo legible.')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        # Un admin de barrio o un super admin
        return self.rol and (self.rol.nombre == 'Administrador' or self.rol.nombre == 'Super Admin')

class Acta(db.Model):
    __tablename__ = 'actas'
    id = db.Column(db.Integer, primary_key=True)
    classification = db.Column(db.String(128))
    body = db.Column(db.Text)
    fecha_creacion = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    puesto_id = db.Column(db.Integer, db.ForeignKey('puestos.id'))
    puesto = db.relationship('Puesto', back_populates='actas')
    documento_url = db.Column(db.String(512))

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))