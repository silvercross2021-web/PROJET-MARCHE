# e-Marché — Gestion anti‑fraude des taxes journalières (Mairie de Treichville)

Application web Django pour gérer un marché municipal avec une logique **anti‑fraude** basée sur :

- **Taxe journalière** (une ligne “à payer” par étal et par jour)
- **Ticket papier = reçu officiel** (1 ticket = 1 paiement, jamais réutilisable)
- **Collecteur = responsable d’un lot/carnet** de tickets (traçabilité complète)

Le projet vise une exploitation terrain réaliste : gestion des étals, commerçants, collecte quotidienne, preuves papier, audit, reporting.

---

## 1) Objectif métier (problème / solution)

### Problème
Sur le terrain, la collecte des taxes journalières est exposée aux risques suivants :

- tickets “inventés” ou réutilisés
- argent collecté sans preuve / reçu
- réconciliation impossible entre tickets remis, tickets utilisés, et argent reversé
- “double paiement” ou paiement enregistré sur un mauvais étal

### Solution (approche anti‑fraude)

- **Chaque jour**, chaque étal occupé a une **taxe journalière attendue**.
- Un **paiement** ne peut exister que si :
  - il correspond à une taxe du jour
  - il utilise un ticket valide, non utilisé, appartenant au collecteur
- Chaque collecteur reçoit un **lot de tickets** (carnet) et ne peut utiliser que ceux‑là.

---

## 2) Fonctionnalités principales

- **Auth & rôles** (administration, saisie, lecture)
- **Tableau de bord** : collecte du jour, retards, tendances
- **Commerçants** : fiche, statut, recherche
- **Étals** : création, attribution, libération
- **Taxes journalières** : génération automatique, statut (dû / payé / annulé)
- **Paiements** : saisie stricte (pas de partiel), ticket obligatoire, reçu
- **Tickets** : suivi, statut, traçabilité
- **Collecteurs & lots de tickets** : remise de carnet, plage de tickets, clôture
- **AuditLog** : traçabilité des actions (création/annulation/modifications)

---

## 3) Règles anti‑fraude (invariants)

- **1 ticket = 1 paiement** (jamais réutilisable)
- Un ticket ne peut être utilisé que s’il est :
  - `statut='disponible'`
  - `utilise=False`
  - non lié à un paiement existant
  - rattaché à un **lot**
  - dont le lot est **ouvert**
  - et dont le lot appartient au **collecteur sélectionné**
- **1 collecteur = 1 lot ouvert maximum** (contrainte DB)
- **Pas de paiement partiel** : le montant payé doit être exactement le montant attendu
- **TaxeJournaliere unique (date, étal)** : impossible de payer 2 fois la même taxe du jour

---

## 4) Rôles & accès (groupes Django)

Groupes typiques :

- **Administrateur** : accès complet (incluant `/admin/`)
- **ResponsableMairie** : accès interface web (dashboard + gestion), **sans accès** à `/admin/`
- **Gestionnaire** : gestion métiers (commerçants/étals/tickets)
- **Caissier** : saisie/modification/annulation paiement
- **Lecteur** : lecture uniquement

Note : le middleware bloque `/admin/` sauf superuser / groupe Administrateur.

---

## 5) Architecture technique (Django)

### Stack

- **Backend** : Django
- **Base de données** : SQLite (dev) — PostgreSQL/MySQL recommandé en prod
- **Front** : templates Django + CSS

### Organisation (simplifiée)

```
etalMarrche/
├── e_marche/                 # settings/urls
├── market/                   # app principale
│   ├── models.py             # modèles (Commercant, Etal, Ticket, Paiement, TaxeJournaliere, Collecteur, LotTickets...)
│   ├── services.py           # règles métier (paiements, taxes, audit)
│   ├── views.py              # vues web
│   ├── urls.py               # routes web (+ endpoint JSON)
│   ├── middleware.py         # contrôle accès /admin/
│   ├── signals.py            # audit automatique
│   └── management/commands/  # commandes (init, groupes, taxes...)
├── templates/market/         # UI (login, dashboard, paiements, collecteurs, lots...)
└── static/css/styles.css
```

---

## 6) Modèle de données (résumé)

- **Secteur** : zone du marché
- **Commercant** : personne/activité
- **Etal** : emplacement (superficie, statut libre/occupé, attribution)
- **TaxeJournaliere** : la ligne “à payer” par date+étal (montant attendu, statut)
- **Collecteur** : agent de collecte terrain
- **LotTickets** : carnet remis à un collecteur (plage début/fin, statut ouvert/clos)
- **Ticket** : numéro unique (reçu papier), rattaché à un lot
- **Paiement** : enregistrement d’une taxe journalière, ticket obligatoire
- **AuditLog** : journal de traçabilité

---

## 7) Installation & démarrage (développement)

### Prérequis

- Python 3.8+
- pip

### Démarrage rapide (Windows)

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py init_data
python manage.py runserver
```

Accès :

- UI : http://127.0.0.1:8000/
- Admin : http://127.0.0.1:8000/admin/ (réservé Admin/superuser)

---

## 8) Commandes de gestion (management commands)

- **Initialiser des données de démo**

```bash
python manage.py init_data
```

- **Créer les groupes/permissions**

```bash
python manage.py create_groups
```

- **Créer un utilisateur ResponsableMairie**

```bash
python manage.py create_responsable_mairie
```

- **Générer les taxes journalières pour une date**

```bash
python manage.py generate_taxes_jour --date 2026-01-15
```

- **Vérifier les retards**

```bash
python manage.py check_retards
```

---

## 9) UX Paiements : sélection ticket selon collecteur (anti‑fraude)

Sur la page Paiements :

- Tu choisis un **collecteur**
- Le champ “Numéro de ticket” propose uniquement les tickets **disponibles** du **lot ouvert** de ce collecteur

Endpoint JSON :

- `GET /api/collecteurs/<id>/tickets-disponibles/`

---

## 10) Scénario complet de démonstration (A → Z)

Ce scénario est conçu pour une démonstration “PowerPoint + live”.

### Phase A — Préparation (Administrateur)

1. Lancer le projet + se connecter en Admin
2. Créer/valider :
   - secteurs
   - commerçants
   - étals (avec superficie)
   - attribution d’étals à des commerçants

### Phase B — Préparer les tickets (Administrateur)

1. Générer des tickets (numéros uniques) si nécessaire
2. Imprimer/organiser en carnets (numérotation continue)

### Phase C — Créer les collecteurs (ResponsableMairie / Admin)

1. Aller sur **Collecteurs**
2. Créer :
   - `KONE IBRAHIM`
   - `ALI TRAORE` (exemple)

### Phase D — Remettre un carnet (lot) à un collecteur

1. Aller sur **Lots de tickets**
2. Créer un lot (statut ouvert) pour `KONE IBRAHIM`
3. Assigner une plage : `T-000401` → `T-000600`
4. Contrôle : le système empêche un lot “chevauchant” ou un 2e lot ouvert

### Phase E — Générer la feuille du jour (taxes)

1. Générer les taxes journalières pour la date du jour :

```bash
python manage.py generate_taxes_jour
```

2. Résultat : chaque étal occupé a une **TaxeJournaliere** “dû”

### Phase F — Collecte terrain (hors système)

Le collecteur encaisse et remet le ticket papier au commerçant.

### Phase G — Saisie des paiements (Caissier / ResponsableMairie)

Pour chaque encaissement terrain :

1. Aller sur **Paiements**
2. Rechercher un commerçant (nom/prénom/numéro d’étal)
3. Choisir le **collecteur**
4. Dans “Numéro de ticket”, taper/sélectionner un ticket proposé (tickets du lot)
5. Le montant est calculé automatiquement depuis la taxe du jour
6. Enregistrer

Contrôles visibles (anti‑fraude) :

- ticket invalide / déjà utilisé → refus
- ticket d’un autre collecteur → refus
- lot clos → refus
- taxe du jour déjà payée → refus
- montant partiel → refus

### Phase H — Reporting (Dashboard / Rapports)

1. Voir le total collecté du jour
2. Voir la liste des commerçants en retard
3. Vérifier les tickets restants / utilisés

---

## 11) Plan de présentation PowerPoint (structure conseillée)

1. **Titre & Contexte**
   - “e‑Marché : digitalisation & anti‑fraude des taxes journalières”

2. **Problématique terrain**
   - tickets, fraude, réconciliation

3. **Solution proposée**
   - taxe journalière + ticket reçu officiel + lot par collecteur

4. **Architecture**
   - Django, modèles, services, audit

5. **Rôles & gouvernance**
   - Admin / ResponsableMairie / Caissier / Lecteur

6. **Règles anti‑fraude (invariants)**
   - 1 ticket = 1 paiement, lot ouvert, pas de partiel, unique(date, étal)

7. **Parcours utilisateur (démo)**
   - remise carnet → collecte → saisie → reporting

8. **Démo live (checklist)**
   - créer collecteur + lot + saisir 1 paiement + montrer refus si fraude

9. **Bénéfices**
   - traçabilité, contrôle, reporting, audit

10. **Roadmap**
   - exports PDF/Excel, déploiement, intégration mobile/scan QR, etc.

---

© 2025–2026 Mairie de Treichville — e‑Marché
#   P R O J E T - M A R C H E  
 