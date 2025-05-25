# Garméa

**Garméa** est un prototype logiciel de reconnaissance d'individus dans les actes historiques français, visant à reconstituer automatiquement les relations familiales et généalogiques à partir de documents historiques.

## Objectifs

- **Extraction automatique** des individus mentionnés dans des documents PDF (actes notariés, registres paroissiaux, etc.)
- **Croisement des données** pour reconstituer les liens familiaux (parenté, alliances, etc.)
- **Reconstruction d'arbres généalogiques** complets et sourcés, basés sur l'analyse sémantique des relations :
  - Parents/enfants (père, mère, fils, fille)
  - Famille élargie (oncles, tantes, cousins, neveux, nièces)
  - Liens sociaux (parrains, marraines)
  
## État actuel

- **Version :** `0.17.20` (prototype en développement actif)
- **Phase :** Entraînement sur textes bruts
- **Période ciblée :** **Ancien Régime** (1540 – avant 1789)  
  *⚠️ Non adapté aux périodes postérieures pour le moment*

## Fonctionnement

Le logiciel analyse les documents pour :
1. Identifier les individus et leurs attributs (noms, dates, métiers, etc.)
2. Interpréter les relations explicites et implicites
3. Déduire des liens familiaux par inférence logique

*Prototype développé à des fins de recherche historique.*