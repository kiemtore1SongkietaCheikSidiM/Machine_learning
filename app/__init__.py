import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from dotenv import load_dotenv
from flask_login import LoginManager

# Charger les variables d'environnement
load_dotenv()

# Instances globales
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()




# ============================================================
#   FACTORY : CRÉATION DE L’APPLICATION FLASK
# ============================================================
def create_app():
    app = Flask(__name__, instance_relative_config=True)

    # -----------------------------
    # CONFIGURATION
    # -----------------------------
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'cle_secrete_defaut')

    # Base de données SQLite dans /instance/site.db
    db_path = os.path.join(app.instance_path, 'site.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # S’assurer que /instance existe
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except Exception:
        pass

    # -----------------------------
    # INITIALISATION EXTENSIONS
    # -----------------------------
    db.init_app(app)
    bcrypt.init_app(app)

    login_manager.init_app(app)
    # Use the connexion_inscription endpoint as the login view (matches templates)
    login_manager.login_view = "main.login"
    login_manager.login_message_category = "info"

    # -----------------------------
    # IMPORTATION & ENREGISTREMENT DES BLUEPRINTS
    # -----------------------------
    from app.routes import main
    app.register_blueprint(main)

    # -----------------------------
    # CREATION DB SI NECESSAIRE
    # -----------------------------
    with app.app_context():
        db.create_all()
    
    

    return app
