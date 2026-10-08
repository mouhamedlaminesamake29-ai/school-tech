SCHOOL.TECH - GUIDE DE DEMARRAGE

1. Installe Python 3 si ce n'est pas déjà fait.
2. Décompresse le dossier School.Tech.
3. Ouvre le dossier.
4. Dans la barre d'adresse de l'Explorateur Windows, écris CMD puis Entrée.
5. Tape :
   python -m pip install -r requirements.txt
6. Puis :
   python app.py
7. Ouvre Chrome et va sur :
   http://127.0.0.1:5000

FONCTIONNALITES DE CETTE VERSION
- création de compte
- connexion sécurisée avec mot de passe haché
- tableau de bord personnel
- ajout de notes par matière et notion
- détection simple des notions sous 10/20
- moyenne personnelle
- gestion de tâches
- données séparées entre les utilisateurs

IMPORTANT
Cette version est un prototype de démonstration. Avant une mise en ligne publique,
il faudra notamment remplacer la clé secrète Flask, désactiver debug=True,
activer HTTPS et renforcer les protections de formulaire/session.
