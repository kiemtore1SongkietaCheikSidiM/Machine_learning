from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime, timedelta


# Charger un utilisateur via Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ============================
#   enregistrement des utilisateurs dans la base de donne
# ============================
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    username = db.Column(db.String(20), unique=True, nullable=False)
    country = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)  # pour Twilio !
    password_hash = db.Column(db.String(100), nullable=False)
    phone_verified = db.Column(db.Boolean, default=False)  # Vérification OTP
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    messages = db.relationship("Message", backref="author", lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.country}')"


# ============================
#   enregistrement de message
# ============================
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_from_user = db.Column(db.Boolean, nullable=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Message('{self.content}', '{self.timestamp}')"


# ============================
#   Enregistrement de historique
# ============================
class Historique(db.Model):
    """Classe pour enregistrer l'historique des interactions du chatbot"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('historiques', lazy=True))
    
    message_utilisateur = db.Column(db.Text, nullable=False)
    reponse_bot = db.Column(db.Text, nullable=False)
    intent_detecte = db.Column(db.String(100), nullable=True)
    confiance = db.Column(db.Float, nullable=True)  # score de confiance (0-1)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"Historique(user_id={self.user_id}, timestamp={self.timestamp})"


# ============================
#   RAPPEL twilio
# ============================
class Rappel(db.Model):
    """Classe pour gérer les rappels Twilio (SMS)"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('rappels', lazy=True))
    
    titre = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    date_rappel = db.Column(db.DateTime, nullable=False)
    statut = db.Column(db.String(20), nullable=False, default='pending')  # pending, sent, snoozed, completed
    
    # Pour Twilio
    numero_telephone = db.Column(db.String(20), nullable=False)
    message_sms = db.Column(db.Text, nullable=True)
    sid_twilio = db.Column(db.String(100), nullable=True)  # SID du message envoyé
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"Rappel(user_id={self.user_id}, titre='{self.titre}', date={self.date_rappel})"
    
    def marquer_envoye(self, sid):
        """Marquer le rappel comme envoyé avec l'ID Twilio"""
        self.statut = 'sent'
        self.sid_twilio = sid
        self.updated_at = datetime.utcnow()
        db.session.commit()
    
    def marquer_complete(self):
        """Marquer le rappel comme complété"""
        self.statut = 'completed'
        self.updated_at = datetime.utcnow()
        db.session.commit()


# ============================
#   OTP 
# ============================
class OTP(db.Model):
    """Classe pour gérer les codes OTP (One-Time Password)"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('otps', lazy=True))
    
    code = db.Column(db.String(10), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    verified = db.Column(db.Boolean, default=False)
    
    expire_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    verified_at = db.Column(db.DateTime, nullable=True)
    
    sid_twilio = db.Column(db.String(100), nullable=True)  # SID du message Twilio
    
    def __repr__(self):
        return f"OTP(user_id={self.user_id}, verified={self.verified})"
    
    def est_expire(self):
        """Vérifier si le code est expiré"""
        return datetime.utcnow() > self.expire_at
    
    def temps_restant(self):
        """Obtenir le temps restant avant expiration (en secondes)"""
        if self.expire_at:
            delta = self.expire_at - datetime.utcnow()
            return max(0, int(delta.total_seconds()))
        return 0


# ============================
#   NOTIFICATION 
# ============================
class Notification(db.Model):
    """Classe pour gérer les notifications SMS"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('notifications', lazy=True))
    
    titre = db.Column(db.String(200), nullable=False)
    contenu = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False, default='sms')  # sms, email, push
    
    envoye = db.Column(db.Boolean, default=False)
    envoye_at = db.Column(db.DateTime, nullable=True)
    lu = db.Column(db.Boolean, default=False)
    lu_at = db.Column(db.DateTime, nullable=True)
    
    sid_twilio = db.Column(db.String(100), nullable=True)  # SID du message Twilio
    statut_twilio = db.Column(db.String(50), nullable=True)  # delivered, failed, read
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"Notification(user_id={self.user_id}, titre='{self.titre}')"
    
    def marquer_lu(self):
        """Marquer la notification comme lue"""
        self.lu = True
        self.lu_at = datetime.utcnow()
        db.session.commit() 