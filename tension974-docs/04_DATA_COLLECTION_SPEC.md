# 04 — Data Collection Specification

## Source

Plateforme : Leboncoin  
Recherche MVP : Saint-Denis - T3  
URL :

```text
https://www.leboncoin.fr/recherche?text=t3&locations=Saint-Denis_97400__-20.89076_55.45851_5000_1000&from=rs
```

## Donnée cible

Texte visible du type : `242 annonces`

Valeur extraite : `242`

## Provider principal : Firecrawl

L'agent développeur doit lire la documentation Firecrawl officielle au moment du build avant d'implémenter les appels API.

Il ne doit pas supposer que les noms d'endpoints ou les formats de payload sont inchangés.

## Stratégie Firecrawl en couches

L'agent doit tester ou prévoir ces modes dans l'ordre :

### Niveau 1 — Markdown

Demander à Firecrawl un contenu textuel/markdown.

Extraction par regex :
- `(\d+[\s\u00a0]*)+ annonce`
- gérer singulier/pluriel ;
- gérer espaces classiques et insécables.

### Niveau 2 — HTML rendu

Si le markdown ne contient pas le compteur, demander ou exploiter le HTML rendu.

Appliquer les mêmes règles d'extraction sur le texte nettoyé.

### Niveau 3 — Extraction structurée

Si Firecrawl supporte une extraction structurée au moment du build, demander un schéma équivalent à :

```json
{
  "total_listings_count": "integer",
  "raw_total_listings_text": "string"
}
```

### Niveau 4 — Screenshot/debug

Prévoir une option de debug permettant de stocker une trace ou des métadonnées utiles si la collecte échoue.

### Niveau 5 — Échec contrôlé

Si aucun compteur n'est trouvé :
- créer un relevé avec statut `failed` ;
- enregistrer l'erreur ;
- conserver un extrait de contenu si possible ;
- ne pas interrompre brutalement le programme.

## Extraction

Créer une fonction pure testable :

```python
extract_total_listings_count(text: str) -> int | None
```

Cas à couvrir :
- `242 annonces` → 242
- `1 annonce` → 1
- `1 234 annonces` → 1234
- `1\u00a0234 annonces` → 1234
- `Aucune annonce` → 0 ou None selon règle explicite
- texte sans compteur → None

## Fallbacks sans Firecrawl

Le code doit permettre d'ajouter un provider alternatif dans une version ultérieure.

Le MVP ne doit pas échouer si le fallback gratuit n'est pas disponible.

Décision :
- Firecrawl est obligatoire pour la validation réelle MVP.
- Les fallbacks gratuits sont une évolution V1.1/V2.
