# 09 — Test Strategy

> ⚠️ **Document historique.** Cette spec décrit l'architecture d'origine du
> MVP (SQLite + Streamlit + cron quotidien sur Kali Linux), remplacée en
> juillet 2026 par : collecte hebdomadaire GitHub Actions → stockage JSONL
> versionné (`data/*.jsonl`) → dashboard statique GitHub Pages (`docs/`).
> Conservée pour référence. Sources à jour : le `README.md` du dépôt et
> `12_DECISION_LOG.md` (DECISION-009 à 012).


## Objectif

Garantir que le projet livré est installable, exécutable et testable.

## Tests unitaires

### Extraction

Tester :
- nombres simples ;
- singulier/pluriel ;
- espaces ;
- espaces insécables ;
- absence de compteur.

### Configuration

Tester :
- chargement YAML ;
- présence de la recherche `saint_denis_t3` ;
- URL correcte.

### Base de données

Tester :
- création tables ;
- insertion observation success ;
- insertion observation failed ;
- lecture observations.

### Collector hors ligne

Tester avec un provider fake :
- contenu avec compteur ;
- contenu sans compteur ;
- erreur provider.

## Tests d'intégration

### Sans clé Firecrawl

Le système doit :
- détecter l'absence de clé ;
- afficher une erreur claire ;
- ne pas casser les tests hors ligne.

### Avec clé Firecrawl

Exécuter :

```bash
python scripts/smoke_firecrawl.py
```

Valider :
- appel réel ;
- contenu récupéré ;
- compteur extrait ;
- observation stockée.

## Dashboard

Vérifier :
- lancement Streamlit ;
- affichage si base vide ;
- affichage avec données de test ;
- affichage erreurs.

## Critère minimal d'acceptation

`pytest` doit passer.

Le smoke test Firecrawl doit être prêt, même s'il ne peut pas être exécuté sans clé API.
