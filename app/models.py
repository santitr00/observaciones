# app/models.py
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, time
from sqlalchemy import UniqueConstraint

@login.user_loader
def load_user(id):
    return db.session.get(User, int(id))

BARRIOS = ['Vida Barrio Cerrado', 'Vida Club de Campo']
PUESTOS = ['PORTERIA PRINCIPAL', 'PORTERIA SECUNDARIA', 'C.O.M.']

# --- Nuevo Modelo para Asignaciones de Puestos ---
class UserPuestoAssignment(db.Model):
    __tablename__ = 'user_puesto_assignment'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    barrio = db.Column(db.String(100), nullable=False, index=True) # Barrio de la asignación
    puesto = db.Column(db.String(100), nullable=False, index=True) # Puesto asignado

    # Constraint para asegurar que la combinación user/barrio/puesto sea única
    __table_args__ = (UniqueConstraint('user_id', 'barrio', 'puesto', name='uq_user_barrio_puesto'),)

    def __repr__(self):
        return f'<UserPuestoAssignment User {self.user_id} to {self.barrio} - {self.puesto}>'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dni = db.Column(db.String(20), index=True, nullable=False)
    nombre_completo = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=True)
    password_hash = db.Column(db.String(256))
    barrio = db.Column(db.String(100), nullable=False, index=True) # Barrio principal del registro User
    zona = db.Column(db.String(100), nullable=False) 
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    # Relación con UserPuestoAssignment
    # Un registro User (DNI+Barrio) puede tener varios puestos asignados en ESE barrio
    puestos_asignados = db.relationship('UserPuestoAssignment',
                                        foreign_keys=[UserPuestoAssignment.user_id],
                                        primaryjoin="and_(User.id==UserPuestoAssignment.user_id, User.barrio==UserPuestoAssignment.barrio)",
                                        backref=db.backref('assigned_user_record', lazy='select'),
                                        lazy='dynamic',
                                        cascade="all, delete-orphan"
    )

    observations = db.relationship('Observation', backref='author', lazy='dynamic')

    __table_args__ = (UniqueConstraint('dni', 'barrio', name='uq_dni_barrio'),)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # Método para obtener los nombres de los puestos asignados en el barrio actual del User
    def get_puestos_asignados_en_barrio(self, barrio_a_consultar):
            if not barrio_a_consultar:
                return []
            asignaciones = db.session.scalars(
                db.select(UserPuestoAssignment.puesto).where(
                    UserPuestoAssignment.user_id == self.id,
                    UserPuestoAssignment.barrio == barrio_a_consultar
                )
            ).all()
            return asignaciones

    def __repr__(self):
        admin_status = " (Admin)" if self.is_admin else ""
        return f'<User {self.nombre_completo} (DNI: {self.dni}) [{self.barrio}]{admin_status}>'


class Observation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    classification = db.Column(db.String(100), nullable=False)
    body = db.Column(db.String(500), nullable=False)
    observation_date = db.Column(db.Date, nullable=False, index=True)
    observation_time = db.Column(db.Time, nullable=False)
    timestamp = db.Column(db.DateTime, index=True, default=lambda: datetime.now(timezone.utc))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    barrio = db.Column(db.String(100), nullable=False, index=True)
    zona = db.Column(db.String(100), nullable=False, index=True) # 'zona' aquí es el puesto de la observación
    filename = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f'<Observation {self.id} [{self.classification}] in {self.barrio}-{self.zona} on {self.observation_date}>'












