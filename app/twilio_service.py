"""
Service Twilio pour gérer :
- OTP (One-Time Password)
- Rappels (Reminders)
- Notifications
"""

import os
import random
import string
from datetime import datetime, timedelta
from twilio.rest import Client


class TwilioService:
    """Service centralisé pour Twilio"""
    
    def __init__(self):
        """Initialiser le client Twilio"""
        self.account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        self.auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        self.phone_sender = os.environ.get('TWILIO_PHONE_NUMBER')
        
        if self.account_sid and self.auth_token:
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
            print("⚠️  Twilio non configuré - variables d'environnement manquantes")
    
    # ============================================================
    # OTP (ONE-TIME PASSWORD)
    # ============================================================
    
    @staticmethod
    def generer_otp(length=6):
        """Générer un code OTP aléatoire"""
        return ''.join(random.choices(string.digits, k=length))
    
    def envoyer_otp(self, user_id, phone_number):
        """
        Générer et envoyer un OTP par SMS
        
        Args:
            user_id: ID de l'utilisateur
            phone_number: Numéro de téléphone (au format +33...)
        
        Returns:
            dict: {'success': bool, 'otp_id': int, 'message': str}
        """
        # Import local pour éviter les imports circulaires
        from app import db
        from app.models import OTP
        
        if not self.client:
            return {'success': False, 'message': 'Twilio non configuré'}
        
        try:
            # Générer le code OTP
            code_otp = self.generer_otp()
            
            # Sauvegarder l'OTP en base
            otp = OTP(
                user_id=user_id,
                code=code_otp,
                phone_number=phone_number,
                expire_at=datetime.utcnow() + timedelta(minutes=10)
            )
            db.session.add(otp)
            db.session.commit()
            
            # Envoyer le SMS
            message = self.client.messages.create(
                body=f"Votre code OTP est : {code_otp}\nValide pendant 10 minutes.",
                from_=self.phone_sender,
                to=phone_number
            )
            
            # Mettre à jour le SID Twilio
            otp.sid_twilio = message.sid
            db.session.commit()
            
            return {
                'success': True,
                'otp_id': otp.id,
                'message': 'OTP envoyé avec succès'
            }
        
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def verifier_otp(self, user_id, code):
        """
        Vérifier un code OTP
        
        Args:
            user_id: ID de l'utilisateur
            code: Le code OTP à vérifier
        
        Returns:
            dict: {'valid': bool, 'message': str}
        """
        # Import local pour éviter les imports circulaires
        from app import db
        from app.models import OTP
        
        try:
            otp = OTP.query.filter_by(
                user_id=user_id,
                code=code,
                verified=False
            ).first()
            
            if not otp:
                return {'valid': False, 'message': 'Code OTP invalide'}
            
            # Vérifier l'expiration
            if datetime.utcnow() > otp.expire_at:
                return {'valid': False, 'message': 'Code OTP expiré'}
            
            # Marquer comme vérifié
            otp.verified = True
            otp.verified_at = datetime.utcnow()
            db.session.commit()
            
            return {'valid': True, 'message': 'Code OTP vérifié avec succès'}
        
        except Exception as e:
            return {'valid': False, 'message': str(e)}
    
    # ============================================================
    # RAPPELS (REMINDERS)
    # ============================================================
    
    def envoyer_rappel(self, rappel_id):
        """
        Envoyer un rappel par SMS
        
        Args:
            rappel_id: ID du rappel
        
        Returns:
            dict: {'success': bool, 'message': str}
        """
        # Import local pour éviter les imports circulaires
        from app import db
        from app.models import Rappel
        
        if not self.client:
            return {'success': False, 'message': 'Twilio non configuré'}
        
        try:
            rappel = Rappel.query.get(rappel_id)
            if not rappel:
                return {'success': False, 'message': 'Rappel non trouvé'}
            
            # Préférer le numéro de l'utilisateur
            phone_number = rappel.numero_telephone or rappel.user.phone_number
            if not phone_number:
                return {'success': False, 'message': 'Numéro de téléphone non disponible'}
            
            # Construire le message SMS
            message_sms = rappel.message_sms or f"Rappel : {rappel.titre}\n{rappel.description or ''}"
            
            # Envoyer le SMS
            message = self.client.messages.create(
                body=message_sms,
                from_=self.phone_sender,
                to=phone_number
            )
            
            # Mettre à jour le rappel
            rappel.marquer_envoye(message.sid)
            
            return {
                'success': True,
                'message': 'Rappel envoyé avec succès',
                'sid': message.sid
            }
        
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    # ============================================================
    # NOTIFICATIONS
    # ============================================================
    
    def envoyer_notification(self, user_id, titre, contenu):
        """
        Envoyer une notification par SMS
        
        Args:
            user_id: ID de l'utilisateur
            titre: Titre de la notification
            contenu: Contenu de la notification
        
        Returns:
            dict: {'success': bool, 'notification_id': int, 'message': str}
        """
        # Import local pour éviter les imports circulaires
        from app import db
        from app.models import User, Notification
        
        if not self.client:
            return {'success': False, 'message': 'Twilio non configuré'}
        
        try:
            user = User.query.get(user_id)
            if not user or not user.phone_number:
                return {'success': False, 'message': 'Utilisateur ou numéro non trouvé'}
            
            # Créer la notification
            notification = Notification(
                user_id=user_id,
                titre=titre,
                contenu=contenu,
                type='sms'
            )
            db.session.add(notification)
            db.session.flush()
            
            # Construire le message SMS
            message_text = f"{titre}\n{contenu}"
            
            # Envoyer le SMS
            message = self.client.messages.create(
                body=message_text,
                from_=self.phone_sender,
                to=user.phone_number
            )
            
            # Sauvegarder le SID Twilio
            notification.sid_twilio = message.sid
            notification.envoye = True
            notification.envoye_at = datetime.utcnow()
            db.session.commit()
            
            return {
                'success': True,
                'notification_id': notification.id,
                'message': 'Notification envoyée avec succès'
            }
        
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def envoyer_notification_multiple(self, user_ids, titre, contenu):
        """
        Envoyer une notification à plusieurs utilisateurs
        
        Args:
            user_ids: Liste d'IDs d'utilisateurs
            titre: Titre de la notification
            contenu: Contenu de la notification
        
        Returns:
            dict: {'success': bool, 'sent': int, 'failed': int}
        """
        sent = 0
        failed = 0
        
        for user_id in user_ids:
            result = self.envoyer_notification(user_id, titre, contenu)
            if result['success']:
                sent += 1
            else:
                failed += 1
        
        return {
            'success': failed == 0,
            'sent': sent,
            'failed': failed,
            'message': f'{sent} envoyées, {failed} échouées'
        }
    
    # ============================================================
    # UTILITAIRES
    # ============================================================
    
    def obtenir_statut_message(self, sid_twilio):
        """
        Obtenir le statut d'un message Twilio
        
        Args:
            sid_twilio: SID du message
        
        Returns:
            dict: {'status': str, 'message': str}
        """
        if not self.client:
            return {'status': 'unknown', 'message': 'Twilio non configuré'}
        
        try:
            message = self.client.messages.get(sid_twilio).fetch()
            return {
                'status': message.status,
                'message': f"Status: {message.status}",
                'price': message.price,
                'date_sent': message.date_sent
            }
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


# Instance singleton
twilio_service = TwilioService()
