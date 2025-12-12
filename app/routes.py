from flask import Blueprint, render_template, url_for, flash, redirect, request, jsonify
from app import db, bcrypt
from app.models import User, Message, Historique, Rappel, OTP, Notification
from app.twilio_service import twilio_service
from flask_login import login_user, current_user, logout_user, login_required
from app.chatbot import get_bot_response
import re

# Création du Blueprint
main = Blueprint("main", __name__)

# ======================================================
# HOME
# ======================================================
@main.route("/home")
@login_required
def home():
    return render_template("chatbot.html",title="Sante maternelle et infantile chatbot")


# ======================================================
# REGISTER
# ======================================================
@main.route("/", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        username = request.form.get("username")
        country = request.form.get("country")
        phone = request.form.get("phone")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        if password != confirm_password:
            flash("Les mots de passe ne correspondent pas.", "danger")
            return redirect(url_for("main.register"))
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Nom d'utilisateur déjà pris.", "danger")
            return redirect(url_for("main.register"))
        

        hashed = bcrypt.generate_password_hash(password).decode("utf-8")

        user = User(
            first_name=first_name,
            last_name=last_name,
            username=username,
            country=country,
            phone_number=phone,
            password_hash=hashed
        )

        db.session.add(user)
        db.session.commit()
        return redirect(url_for("main.home"))

    return render_template("register.html", title="Inscription au chatbot")


# Aliases to match template and flask-login expectations
@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            next_page = request.args.get("next")
            return redirect(next_page) if next_page else redirect(url_for("main.home"))
        else:
            flash("Nom d'utilisateur ou mot de passe incorrect.", "danger")
        if current_user.is_authenticated:
            return redirect(url_for("main.home"))
    return render_template("login.html", title="Connexion sur le chatbot")
    
@main.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.login"))



# ======================================================
# CHATBOT API
# ======================================================
@main.route("/api/chat", methods=['POST'])
@login_required
def chatbot():
    data = request.get_json()
    # Vérification de la présence du message
    if not data or "message" not in data:
        return jsonify({"error": "Message non fourni"}), 400
    user_message = data["message"].strip()
    if not user_message:
        return jsonify({"error": "Message vide"}), 400
    # Enregistrement du message utilisateur
    user_msg = Message(
        content=user_message,
        is_from_user=True,
        author=current_user
    )
    db.session.add(user_msg)
    # Envoi du message au chatbot et obtention de la réponse
    try:
        bot_reply = get_bot_response(user_message)
    except Exception as e:
        print("Erreur chatbot :", e)
        bot_reply = "Désolé, une erreur est survenue."
    
    bot_msg = Message(
        content=bot_reply,
        is_from_user=False,
        author=current_user
    )
    db.session.add(bot_msg)
    db.session.commit()

    

    return jsonify({"response": bot_reply})
    


# ======================================================
# HISTORY
# ======================================================
@main.route("/api/history")
@login_required
def history():
    messages = Message.query.filter_by(user_id=current_user.id).order_by(Message.timestamp).all()

    data = [
        {
            "content": m.content,
            "timestamp": m.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "is_from_user": m.is_from_user
        }
        for m in messages
    ]

    return jsonify(data)


# ======================================================
# TWILIO - OTP
# ======================================================

@main.route("/api/otp/send", methods=['POST'])
def send_otp():
    """Envoyer un code OTP à l'utilisateur"""
    data = request.get_json()
    phone_number = data.get('phone_number')
    user_id = data.get('user_id')
    
    if not phone_number or not user_id:
        return jsonify({'error': 'Données manquantes'}), 400
    
    # Valider le format du numéro
    if not re.match(r'^\+\d{10,15}$', phone_number):
        return jsonify({'error': 'Format de numéro invalide'}), 400
    
    result = twilio_service.envoyer_otp(user_id, phone_number)
    return jsonify(result)


@main.route("/api/otp/verify", methods=['POST'])
def verify_otp():
    """Vérifier un code OTP"""
    data = request.get_json()
    user_id = data.get('user_id')
    code = data.get('code')
    
    if not user_id or not code:
        return jsonify({'error': 'Données manquantes'}), 400
    
    result = twilio_service.verifier_otp(user_id, code)
    
    if result['valid']:
        # Mettre à jour le statut de vérification
        user = User.query.get(user_id)
        if user:
            user.phone_verified = True
            db.session.commit()
    
    return jsonify(result)


# ======================================================
# TWILIO - RAPPELS
# ======================================================

@main.route("/api/rappel/creer", methods=['POST'])
@login_required
def creer_rappel():
    """Créer un nouveau rappel"""
    data = request.get_json()
    
    titre = data.get('titre')
    description = data.get('description')
    date_rappel = data.get('date_rappel')
    message_sms = data.get('message_sms')
    
    if not titre or not date_rappel:
        return jsonify({'error': 'Titre et date requis'}), 400
    
    try:
        from datetime import datetime
        date_obj = datetime.fromisoformat(date_rappel)
        
        rappel = Rappel(
            user_id=current_user.id,
            titre=titre,
            description=description,
            date_rappel=date_obj,
            numero_telephone=current_user.phone_number,
            message_sms=message_sms or f"Rappel: {titre}"
        )
        
        db.session.add(rappel)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'rappel_id': rappel.id,
            'message': 'Rappel créé avec succès'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@main.route("/api/rappel/envoyer/<int:rappel_id>", methods=['POST'])
@login_required
def envoyer_rappel(rappel_id):
    """Envoyer un rappel par SMS"""
    result = twilio_service.envoyer_rappel(rappel_id)
    return jsonify(result)


@main.route("/api/rappel/liste", methods=['GET'])
@login_required
def liste_rappels():
    """Lister tous les rappels de l'utilisateur"""
    rappels = Rappel.query.filter_by(user_id=current_user.id).order_by(Rappel.date_rappel).all()
    
    data = [
        {
            'id': r.id,
            'titre': r.titre,
            'description': r.description,
            'date_rappel': r.date_rappel.isoformat(),
            'statut': r.statut,
            'created_at': r.created_at.isoformat()
        }
        for r in rappels
    ]
    
    return jsonify(data)


# ======================================================
# TWILIO - NOTIFICATIONS
# ======================================================

@main.route("/api/notification/envoyer", methods=['POST'])
@login_required
def envoyer_notification():
    """Envoyer une notification"""
    data = request.get_json()
    
    titre = data.get('titre')
    contenu = data.get('contenu')
    user_id = data.get('user_id', current_user.id)
    
    if not titre or not contenu:
        return jsonify({'error': 'Titre et contenu requis'}), 400
    
    # Vérifier les permissions (ne pas pouvoir envoyer à quelqu'un d'autre)
    if user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Non autorisé'}), 403
    
    result = twilio_service.envoyer_notification(user_id, titre, contenu)
    return jsonify(result)


@main.route("/api/notification/liste", methods=['GET'])
@login_required
def liste_notifications():
    """Lister les notifications de l'utilisateur"""
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    
    data = [
        {
            'id': n.id,
            'titre': n.titre,
            'contenu': n.contenu,
            'envoye': n.envoye,
            'lu': n.lu,
            'created_at': n.created_at.isoformat()
        }
        for n in notifications
    ]
    
    return jsonify(data)


@main.route("/api/notification/<int:notification_id>/lire", methods=['PUT'])
@login_required
def marquer_notification_lue(notification_id):
    """Marquer une notification comme lue"""
    notification = Notification.query.get(notification_id)
    
    if not notification or notification.user_id != current_user.id:
        return jsonify({'error': 'Non trouvé'}), 404
    
    notification.marquer_lu()
    return jsonify({'success': True, 'message': 'Notification marquée comme lue'})


@main.route("/api/notification/envoyer-multiple", methods=['POST'])
@login_required
def envoyer_notification_multiple():
    """Envoyer une notification à plusieurs utilisateurs (admin seulement)"""
    if not hasattr(current_user, 'is_admin') or not current_user.is_admin:
        return jsonify({'error': 'Non autorisé'}), 403
    
    data = request.get_json()
    user_ids = data.get('user_ids', [])
    titre = data.get('titre')
    contenu = data.get('contenu')
    
    if not user_ids or not titre or not contenu:
        return jsonify({'error': 'Données manquantes'}), 400
    
    result = twilio_service.envoyer_notification_multiple(user_ids, titre, contenu)
    return jsonify(result)


# ======================================================
# HISTORIQUE
# ======================================================

@main.route("/api/historique/enregistrer", methods=['POST'])
@login_required
def enregistrer_historique():
    """Enregistrer une interaction dans l'historique"""
    data = request.get_json()
    
    historique = Historique(
        user_id=current_user.id,
        message_utilisateur=data.get('message_utilisateur'),
        reponse_bot=data.get('reponse_bot'),
        intent_detecte=data.get('intent_detecte'),
        confiance=data.get('confiance')
    )
    
    db.session.add(historique)
    db.session.commit()
    
    return jsonify({'success': True, 'id': historique.id})


@main.route("/api/historique", methods=['GET'])
@login_required
def consulter_historique():
    """Consulter l'historique de l'utilisateur"""
    page = request.args.get('page', 1, type=int)
    par_page = request.args.get('per_page', 20, type=int)
    
    historiques = Historique.query.filter_by(user_id=current_user.id).order_by(Historique.timestamp.desc()).paginate(page=page, per_page=par_page)
    
    data = [
        {
            'id': h.id,
            'message_utilisateur': h.message_utilisateur,
            'reponse_bot': h.reponse_bot,
            'intent_detecte': h.intent_detecte,
            'confiance': h.confiance,
            'timestamp': h.timestamp.isoformat()
        }
        for h in historiques.items
    ]
    
    return jsonify({
        'data': data,
        'total': historiques.total,
        'pages': historiques.pages,
        'page': page
    })


# ======================================================
# TEST SMS
# ======================================================

@main.route("/test_sms")
@login_required
def test_sms():
    """Test d'envoi SMS"""
    if not current_user.phone_number:
        flash("Numéro de téléphone non défini", "danger")
        return redirect(url_for("main.home"))
    
    result = twilio_service.envoyer_notification(
        current_user.id,
        "Test SMS",
        "Ceci est un message de test de votre chatbot de santé maternelle."
    )
    
    if result['success']:
        flash("SMS de test envoyé !", "success")
    else:
        flash(f"Erreur: {result['message']}", "danger")
    
    return redirect(url_for("main.home"))