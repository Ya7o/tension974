# 02 — Functional Specification

> ⚠️ **Document historique.** Cette spec décrit l'architecture d'origine du
> MVP (SQLite + Streamlit + cron quotidien sur Kali Linux), remplacée en
> juillet 2026 par : collecte hebdomadaire GitHub Actions → stockage JSONL
> versionné (`data/*.jsonl`) → dashboard statique GitHub Pages (`docs/`).
> Conservée pour référence. Sources à jour : le `README.md` du dépôt et
> `12_DECISION_LOG.md` (DECISION-009 à 012).


## Fonctionnalités MVP

### F1 — Configuration de recherche

L'application doit lire un fichier `config/searches.yaml`.

Pour le MVP, ce fichier contient une recherche active :

```yaml
searches:
  - id: saint_denis_t3
    name: "Saint-Denis - T3"
    platform: "leboncoin"
    url: "https://www.leboncoin.fr/recherche?text=t3&locations=Saint-Denis_97400__-20.89076_55.45851_5000_1000&from=rs"
    location: "Saint-Denis, La Réunion"
    property_type: "T3"
    metric: "total_listings_count"
    active: true
```

### F2 — Collecte manuelle

Une commande doit permettre de lancer une collecte immédiatement :

```bash
python scripts/collect.py
```

La commande doit :
1. lire la configuration ;
2. appeler le provider de collecte ;
3. extraire le nombre d'annonces ;
4. enregistrer le résultat en base ;
5. écrire des logs.

### F3 — Collecte planifiée

Une entrée cron doit permettre l'exécution tous les soirs à 21h15.

### F4 — Stockage historique

Chaque collecte doit créer un relevé horodaté.

Si l'extraction échoue, l'échec doit être enregistré avec un statut d'erreur au lieu de casser silencieusement.

### F5 — Dashboard

Le dashboard Streamlit doit afficher :
- le dernier relevé ;
- la variation 7 jours si disponible ;
- la variation 30 jours si disponible ;
- la courbe historique ;
- le tableau des relevés ;
- les erreurs récentes.

### F6 — Export CSV

Une commande doit permettre d'exporter les relevés en CSV.

### F7 — Gestion sans clé API

Si `FIRECRAWL_API_KEY` est absente :
- le programme ne doit pas planter brutalement ;
- les tests hors ligne doivent rester exécutables ;
- un message clair doit expliquer que le test réel Firecrawl est impossible.
