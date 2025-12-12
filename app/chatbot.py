import json
import random
import os
import nltk
from datetime import datetime, timedelta
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- État global pour suivre si le bot attend des dates ---
awaiting_due_date = False
calendar_vaccination = False

# Initialisation du lemmatiseur
lemmatizer = WordNetLemmatizer()

# --- CHARGEMENT DU CORPUS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CORPUS_PATH = os.path.join(BASE_DIR, "corpus.json")

with open(CORPUS_PATH, "r", encoding="utf-8") as file:
    data = json.load(file)

# --- PRETRAITEMENT DU CORPUS ---
patterns = []
tags = []
responses_dict = {}

for intent in data.get("intents", []):
    tag = intent.get("tag")
    responses = intent.get("responses", [])
    patterns_list = intent.get("patterns", [])

    if not tag or not responses or not isinstance(patterns_list, list):
        continue

    responses_dict[tag] = responses

    for pattern in patterns_list:
        if isinstance(pattern, str) and pattern.strip():
            patterns.append(pattern)
            tags.append(tag)

# --- FONCTION DE PRETRAITEMENT ---
def preprocess_text(text):
    tokens = nltk.word_tokenize(text.lower())
    lemmas = [lemmatizer.lemmatize(token) for token in tokens]
    return " ".join(lemmas)

# --- VECTORIZATION TF-IDF ---
processed_patterns = [preprocess_text(p) for p in patterns]

vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(processed_patterns)

# ==================================================
# 🔵 FONCTION: Génération du calendrier de grossesse
# ==================================================
def generate_pregnancy_calendar(due_date_str):
    try:
        due = datetime.strptime(due_date_str, "%d/%m/%Y")
    except ValueError:
        return "La date n'est pas valide ❗ Utilise le format JJ/MM/AAAA."

    today = datetime.today()
    conception = due - timedelta(days=280)
    weeks_pregnant = (today - conception).days // 7
    weeks_remaining = (due - today).days // 7

    return (
        f"🤰 **Calendrier de votre grossesse :**\n\n"
        f"📅 **Date prévue d'accouchement :** {due.strftime('%d %B %Y')}\n"
        f"🌱 **Date probable de conception :** {conception.strftime('%d %B %Y')}\n"
        f"👶 **Âge actuel de grossesse :** {weeks_pregnant} semaines\n"
        f"⏳ **Semaines restantes :** {weeks_remaining} semaines\n\n"
        f"Souhaitez-vous un calendrier détaillé mois par mois ? 😊"
    )

def generate_vaccination_calendar(birth_date_str):
    try:
        birth_date = datetime.strptime(birth_date_str, "%d/%m/%Y")
    except ValueError:
        return "La date n'est pas valide ❗ Utilise le format JJ/MM/AAAA."
    #source: https://fr.scribd.com/document/826040237/CALENDRIER-VACCINAL-0001  du Ministère de la Santé Burkinabé du 30 janvier 2025
    vaccination_schedule = [
        ("BCG", 0),
        ("Hépatite B", 0),
        ("VPO",0),
        ("DTC-Hepatite-B Hib2", 2),
        ("VPO 1",2),
        ("Pneumo 1 PCV13",2),
        ("Rota 1",2),
        ("DTC-HepB-Hib 2",3),
        ("VPO 2",3),
        ("Rota 2",3),
        ("DTC-HepB-Hib 3",4),
        ("VPO 3",4),
        ("Pneumo 2",4),
        ("Rota 3",4),
        ("VPI",4),
        ("Vaccin anti paludique 1",5),
        ("Vaccin anti paludique 2",6),
        ("Vaccin anti paludique 3",7),
        ("RR 1",9),
        ("VAA",9),
        ("VTC fievre typhoide",9),
        ("VPI 2",9),
        ("RR 2",15),
        ("Men A MenAfricVac",15,),
        ("Pneumo 3 PCV 13",23),
        ("Vaccin anti-paludique 4",23),
    ]

    response = "💉 **Calendrier de vaccination pour votre enfant :**\n\n"
    for vaccine, months in vaccination_schedule:
        vaccination_date = birth_date + timedelta(days=months * 30)
        response += f"• {vaccine} : {vaccination_date.strftime('%d %B %Y')}\n"

    return response

# ==================================================
# 🔵 FONCTION PRINCIPALE
# ==================================================
def get_bot_response(user_input):
    global calendar_vaccination
    if calendar_vaccination:
        calendar_vaccination = False
        return generate_vaccination_calendar(user_input)
    global awaiting_due_date

    # Si le bot attend une date
    if awaiting_due_date:
        awaiting_due_date = False
        return generate_pregnancy_calendar(user_input)

    # Traitement normal TF-IDF
    processed_input = preprocess_text(user_input)
    input_vec = vectorizer.transform([processed_input])

    similarities = cosine_similarity(input_vec, X)
    best_idx = similarities.argmax()
    best_score = similarities[0, best_idx]

    if best_score > 0.20:
        tag = tags[best_idx]

        # Si l'intent détecté est celui qui nécessite une date
        if tag == "Savoir_approximation_grossesse":
            awaiting_due_date = True
            return random.choice(responses_dict[tag])
        
        if tag == "Approximation_calendrier_vaccination_jeune_enfant":
            calendar_vaccination = True
            return random.choice(responses_dict[tag])


        # Sinon réponse normale
        return random.choice(responses_dict[tag])
        

    return "Je peux vous aider sur la grossesse 🤰, le bébé 👶, les visites prénatales, l’alimentation 🍎 ou la vaccination 💉. Que souhaitez-vous savoir ?"
