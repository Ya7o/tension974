# 14 — Acceptance Checklist

> ⚠️ **Document historique.** Cette spec décrit l'architecture d'origine du
> MVP (SQLite + Streamlit + cron quotidien sur Kali Linux), remplacée en
> juillet 2026 par : collecte hebdomadaire GitHub Actions → stockage JSONL
> versionné (`data/*.jsonl`) → dashboard statique GitHub Pages (`docs/`).
> Conservée pour référence. Sources à jour : le `README.md` du dépôt et
> `12_DECISION_LOG.md` (DECISION-009 à 012).


L'agent IA doit remplir cette checklist avant de considérer le projet terminé.

## Structure

- [ ] La structure projet existe.
- [ ] Le nom `tension974` est utilisé.
- [ ] Le README d'installation existe.
- [ ] `.env.example` existe.
- [ ] `config/searches.yaml` existe.

## Configuration

- [ ] La recherche `saint_denis_t3` est présente.
- [ ] L'URL Leboncoin MVP est correcte.
- [ ] La clé Firecrawl est lue depuis `.env`.

## Base de données

- [ ] SQLite est initialisé.
- [ ] Les tables existent.
- [ ] Une observation success peut être insérée.
- [ ] Une observation failed peut être insérée.

## Extraction

- [ ] `242 annonces` donne `242`.
- [ ] `1 annonce` donne `1`.
- [ ] `1 234 annonces` donne `1234`.
- [ ] Un texte sans compteur est géré proprement.

## Collecte

- [ ] Le collector peut être lancé manuellement.
- [ ] L'absence de clé API est gérée proprement.
- [ ] Le provider Firecrawl existe.
- [ ] Le smoke test Firecrawl existe.
- [ ] Si une clé API est disponible, le smoke test a été exécuté.

## Dashboard

- [ ] Streamlit se lance.
- [ ] Le dashboard gère une base vide.
- [ ] Le dashboard affiche les données de test.
- [ ] Le dashboard affiche les erreurs.

## Tests

- [ ] `pytest` passe.
- [ ] Les tests couvrent extraction/config/database/collector offline.
- [ ] Les échecs sont corrigés avant livraison.

## Cron

- [ ] Un exemple crontab est fourni.
- [ ] La planification 21h15 est documentée.
- [ ] Les logs cron sont documentés.

## Rapport final

- [ ] Ce qui a été testé est listé.
- [ ] Ce qui n'a pas pu être testé est listé.
- [ ] Les prochaines actions sont claires.
