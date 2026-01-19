# e-Marché - Plateforme de Gestion des Marchés Municipaux

Application web pour la gestion des marchés municipaux de la Mairie de Treichville.

## Structure du Projet

```
etalMarrche/
├── index.html          # Page de connexion
├── dashboard.html      # Tableau de bord
├── commercants.html    # Gestion des commerçants
├── etals.html         # Gestion des étals
├── tickets.html       # Gestion des tickets
├── paiements.html     # Saisie des paiements
├── rapports.html      # Rapports
├── css/
│   └── styles.css     # Fichier CSS principal
└── README.md          # Documentation
```

## Pages Disponibles

1. **Page de Connexion** (`index.html`)
   - Formulaire d'authentification
   - Design centré avec logo de la mairie

2. **Tableau de Bord** (`dashboard.html`)
   - Indicateurs clés de performance (KPI)
   - Graphiques de collecte journalière et mensuelle
   - Statut des tickets

3. **Gestion des Commerçants** (`commercants.html`)
   - Liste des commerçants avec recherche
   - Statut de paiement de chaque commerçant

4. **Gestion des Étals** (`etals.html`)
   - Vue d'ensemble des étals (occupés/libres)
   - Filtres par statut
   - Détails de chaque étal

5. **Saisie des Paiements** (`paiements.html`)
   - Formulaire de saisie de paiement
   - Liste des paiements récents
   - Résumé journalier

6. **Gestion des Tickets** (`tickets.html`)
   - Liste des tickets avec recherche
   - Statut d'utilisation

7. **Rapports** (`rapports.html`)
   - Filtres de rapport (hebdomadaire, mensuel, personnalisé)
   - Aperçu du rapport avec export PDF/Excel
   - Tableau détaillé des collectes

## Utilisation

1. Ouvrir `index.html` dans un navigateur web
2. Se connecter avec les identifiants
3. Naviguer entre les différentes sections via le menu latéral

## Caractéristiques

- Design moderne et responsive
- Navigation intuitive avec sidebar
- Tableaux interactifs avec recherche
- Graphiques de visualisation des données
- Interface cohérente sur toutes les pages
- Couleurs conformes à l'identité visuelle de la mairie

## Technologies Utilisées

- HTML5
- CSS3 (Variables CSS, Flexbox, Grid)
- Design responsive

## Notes

- Les données affichées sont des exemples statiques
- Pour une utilisation en production, il faudra intégrer un backend pour la gestion des données
- Les fonctionnalités d'export PDF/Excel nécessitent une implémentation JavaScript

