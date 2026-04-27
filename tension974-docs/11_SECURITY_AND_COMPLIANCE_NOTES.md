# 11 — Security and Compliance Notes

## Données collectées

Le MVP collecte uniquement :
- un chiffre agrégé ;
- une date de relevé ;
- l'URL de recherche ;
- des métadonnées techniques de collecte.

Le MVP ne collecte pas :
- noms ;
- numéros de téléphone ;
- emails ;
- détails d'annonces ;
- photos ;
- informations personnelles.

## Fréquence raisonnable

La collecte est limitée à :
- une URL ;
- une fois par jour ;
- à 21h15.

## Firecrawl

Firecrawl est utilisé pour fiabiliser techniquement la récupération d'une page publique.

Il ne doit pas être présenté comme une garantie de légalité.

La conformité dépend aussi :
- des conditions d'utilisation des sites consultés ;
- de la fréquence ;
- du type de données collectées ;
- de l'usage final.

## Secrets

La clé Firecrawl doit être stockée dans `.env`.

Ne jamais commiter :
- `.env`
- base SQLite réelle si elle contient des logs sensibles ;
- captures debug contenant potentiellement du contenu tiers.

## Logs

Les logs doivent éviter de stocker des contenus complets de page.

Conserver seulement :
- statut ;
- message d'erreur ;
- extrait court si utile au debug.
