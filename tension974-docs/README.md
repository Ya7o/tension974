# tension974 — Pack documentaire de cadrage

Ce dossier contient les documents de cadrage nécessaires pour faire développer le MVP du projet **tension974** par un agent IA développeur.

## Objectif

Automatiser le suivi quotidien du nombre total d'annonces Leboncoin correspondant à une recherche locative précise à La Réunion.

- Recherche MVP : Saint-Denis - T3
- Source : Leboncoin
- URL : https://www.leboncoin.fr/recherche?text=t3&locations=Saint-Denis_97400__-20.89076_55.45851_5000_1000&from=rs
- Métrique : nombre total d'annonces affiché, par exemple `242 annonces`
- Fréquence : tous les soirs à 21h15
- Environnement : Kali Linux, Python, accès SSH
- Dashboard : Streamlit
- Stockage : SQLite + export CSV
- Collecte : Firecrawl comme provider principal

## Usage prévu

Ce pack doit être donné à un agent IA développeur qui doit coder le projet complet sans interaction utilisateur.

L'agent doit :
1. lire tous les documents ;
2. respecter le périmètre MVP ;
3. coder l'application ;
4. créer les tests ;
5. exécuter les tests ;
6. documenter ce qui est validé ;
7. ne pas déclarer le projet terminé tant que les critères d'acceptation ne sont pas couverts.

## Documents

- `00_PROJECT_BRIEF.md` : vision courte du projet.
- `01_PRODUCT_SPEC.md` : spécification produit.
- `02_FUNCTIONAL_SPEC.md` : fonctionnalités attendues.
- `03_TECHNICAL_SPEC.md` : architecture technique.
- `04_DATA_COLLECTION_SPEC.md` : collecte Firecrawl et extraction.
- `05_DATA_MODEL.md` : modèle SQLite.
- `06_DASHBOARD_SPEC.md` : dashboard Streamlit.
- `07_AI_AGENT_BUILD_INSTRUCTIONS.md` : instructions strictes pour agent IA.
- `08_DEVELOPMENT_PLAN.md` : plan de développement.
- `09_TEST_STRATEGY.md` : stratégie de tests.
- `10_DEPLOYMENT_GUIDE_KALI.md` : guide de déploiement Kali Linux.
- `11_SECURITY_AND_COMPLIANCE_NOTES.md` : limites conformité et sécurité.
- `12_DECISION_LOG.md` : journal des décisions.
- `13_ROADMAP.md` : évolutions futures.
- `14_ACCEPTANCE_CHECKLIST.md` : checklist de livraison.
- `15_UI_AUDIT_ET_PARCOURS.md` : audit de l'interface et parcours utilisateur
  ayant motivé la refonte UI (spec de la vue résultante : section V3 de
  `06_DASHBOARD_SPEC.md`).

## Important

Le MVP ne doit pas chercher à scraper toutes les annonces. Il doit uniquement récupérer un chiffre agrégé : le nombre total d'annonces pour la recherche configurée.
