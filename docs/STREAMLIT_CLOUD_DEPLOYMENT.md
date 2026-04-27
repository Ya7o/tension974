# Deploiement Streamlit Community Cloud

## Entree principale

L'application Streamlit principale est :

```text
dashboard.py
```

## Prerequis

- Le repo GitHub `Ya7o/tension974` contient le code a jour.
- Le Google Sheet est partage avec l'adresse email du Service Account.
- Le workflow GitHub Actions ecrit dans les onglets `observations`, `runs` et `searches`.
- Les dependances sont declarees dans `requirements.txt`.

## Creer l'application

1. Ouvrir https://share.streamlit.io/.
2. Cliquer sur `New app`.
3. Choisir le repo `Ya7o/tension974`.
4. Choisir la branche `main`.
5. Renseigner `dashboard.py` comme main file path.
6. Valider le deploiement.

## Configurer les secrets Streamlit

Dans l'application Streamlit Cloud, ouvrir `Settings` puis `Secrets` et ajouter :

```toml
TENSION974_STORAGE = "google_sheets"
GOOGLE_SHEET_ID = "your_google_sheet_id"

[google_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "replace-me"
private_key = """
paste the private_key value here
with its real line breaks
"""
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "replace-me"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com"
universe_domain = "googleapis.com"
```

Le format `[google_service_account]` evite les erreurs JSON autour de `private_key`. Ne pas ajouter de fichier `credentials.json` dans le repo.

## Verifier

1. Redemarrer l'application apres modification des secrets.
2. Ouvrir le dashboard.
3. Verifier dans la sidebar :
   - Source : `Google Sheets`
   - Nombre de releves superieur a 0
   - Dernier releve renseigne
4. Verifier que les cartes `stock actuel`, `variation 7 jours`, `variation 30 jours` et `historique` s'affichent.
5. Verifier la section `Dernieres collectes` si l'onglet `runs` contient des lignes.

## Fallback local SQLite

En local, sans secret Streamlit et sans variable `TENSION974_STORAGE`, le dashboard lit SQLite :

```bash
streamlit run dashboard.py
```

Pour forcer Google Sheets localement :

```bash
export TENSION974_STORAGE=google_sheets
export GOOGLE_SHEET_ID="your_google_sheet_id"
export GOOGLE_SERVICE_ACCOUNT_JSON='paste_the_full_google_service_account_json_here'
streamlit run dashboard.py
```
