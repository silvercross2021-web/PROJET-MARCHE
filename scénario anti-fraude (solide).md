1) Le meilleur scénario anti-fraude (solide) : “Ticket = reçu officiel” + “Journée = ligne à payer” + “Collector = responsable d’un lot”
Tu veux 3 choses en même temps :

taxe journalière calculée automatiquement (m² × tarif/jour),
tickets pré-faits (papier) remis aux collecteurs,
traçabilité complète : combien reçus, combien utilisés, combien retournés/perdus, et éviter toute fraude.
La logique la plus robuste (et simple à auditer) est :

Un ticket papier = une preuve et correspond à un paiement unique.
Chaque jour, chaque étal occupé génère une ligne “à payer aujourd’hui”.
Chaque collecteur reçoit un lot numéroté de tickets (carnet), et tout ce qui n’est pas utilisé doit être retourné ou déclaré perdu/annulé.
2) Modèle métier (conceptuel) à mettre en place
A) Collecteur
Même si le collecteur n’a pas accès au site, il faut le référencer :

nom, prenom
contact
actif (oui/non)
B) Carnet / LotTickets (distribution)
But : savoir exactement quels tickets ont été remis à quel collecteur.

Champs conseillés :

collecteur
date_remise
remis_par (admin)
statut : ouvert / clos
ticket_debut, ticket_fin (plage) ou relation vers une liste de tickets
Compteurs calculés :
nb_remis
nb_utilises
nb_restants
nb_perdus_annules
Règle anti-fraude :

Un ticket ne peut être remis qu’à un seul collecteur (via un carnet/lot).
Un ticket utilisé doit forcément avoir un paiement lié.
C) Ticket (amélioration de logique)
Tu as déjà : numero, statut, date_creation, date_utilisation, utilise.

Pour une logique béton :

Garde un seul indicateur (ex: statut), et évite le duo utilise + statut.
Ajoute conceptuellement :
lot / collecteur (via LotTickets)
valeur_theorique (optionnel, voir section “tickets par montant”)
Règles anti-fraude :

Ticket.numero unique (déjà OK)
Un ticket ne peut avoir qu’un seul paiement (déjà presque OK par checks)
date_utilisation doit être la date réelle de collecte (pas la date de saisie)
D) TaxeJournaliere (la pièce maîtresse)
Pour distinguer “a payé aujourd’hui / n’a pas payé / retard”, il faut une table journal.

Champs :

date
etal (et donc commercant via etal)
montant_attendu (calculé)
montant_paye (0 par défaut)
statut : du / paye / partiel / annule
paiement (lien vers Paiement, optionnel si partiel multiple)
Contrainte :

unique(date, etal)
Pourquoi c’est anti-fraude ?

Impossible de “payer 2 fois le même jour” pour le même étal.
Le retard est objectif : statut != paye ET date < aujourd’hui.
E) Paiement
Tu l’as déjà, mais pour taxe journalière il faut :

date_paiement = date/heure réelle de collecte (saisie par admin)
ticket obligatoire (recommandé pour contrôle)
enregistre_par = admin
etal obligatoire (recommandé)
3) Tickets “de tel montant selon m²” : la meilleure approche
Tu as deux approches possibles. La plus solide est :

Approche recommandée : ticket sans montant fixe, montant calculé par l’étal
Le ticket est un reçu avec un numéro unique.
Le montant vient de la règle : superficie × tarif_journalier_par_m2.
Sur le ticket papier, tu imprimes :
numéro ticket
date (écrite par le collecteur)
étal (écrit ou tamponné)
montant payé (écrit)
signature/tampon
Avantages

Si le tarif change (secteur), tu ne détruis pas des carnets.
Pas besoin d’avoir 50 types de tickets.
Approche alternative (moins flexible) : ticket pré-imprimé par valeur
Ex: “Ticket 500 FCFA”, “Ticket 1000 FCFA”, etc. Ça marche si tu as très peu de montants possibles.

Mais pour la superficie (m²) ça devient vite compliqué (trop de valeurs).

Donc : je te conseille ticket “reçu officiel” sans valeur fixe + montant calculé dans le système.

4) Scénario complet de A à Z (sans impasse)
Phase 0 — Paramétrage (admin)
L’admin crée :
secteurs + tarif_journalier_par_m2
étals avec superficie
attribution étal → commerçant (déjà dans ton système)
L’admin crée des collecteurs (liste).
Phase 1 — Création des tickets (admin)
L’admin génère N tickets dans le système (ex: 10 000).
Les tickets sont imprimés en carnets avec numéros consécutifs.
Contrôle

Les numéros doivent être continus par carnet (facilite audit).
Exemple : Carnet C1 = T-000001 → T-000200.
Phase 2 — Remise d’un carnet à un collecteur (admin)
L’admin crée un LotTickets :
collecteur = Ali
plage = T-000001 → T-000200
date_remise = aujourd’hui
statut = ouvert
Contrôle anti-fraude

Un ticket déjà remis à un autre collecteur ne peut pas être remis deux fois.
Phase 3 — Collecte sur le terrain (collecteur)
Pour chaque étal occupé qui paye aujourd’hui :
le collecteur encaisse
remet le ticket papier au commerçant
note sur son registre : (date, étal, montant, ticket_no)
Point clé anti-fraude

Le commerçant conserve le ticket = preuve.
Le collecteur ne peut pas “inventer” un ticket : les tickets sont déjà connus en base.
Phase 4 — Retour de tournée (collecteur → admin)
Le collecteur revient avec :

l’argent
le registre (ou feuille de collecte)
les tickets non utilisés du carnet
Phase 5 — Réconciliation carnet (admin)
Avant même de saisir les paiements, l’admin fait 3 chiffres :

nb_remis (fixe)
nb_utilises (selon les tickets mentionnés dans la feuille)
nb_retournes (tickets physiques non utilisés rendus)
nb_perdus = nb_remis - nb_utilises - nb_retournes
Règle

Tout ticket non rendu doit être déclaré :
perdu / annulé avec motif Sinon, fraude possible (ticket disparu + argent disparu).
Phase 6 — Création automatique de la “Feuille du jour” (système)
Chaque matin (ou à l’ouverture), le système génère TaxeJournaliere pour tous les étals occupés :

date = aujourd’hui
montant_attendu = superficie × tarif_journalier_par_m2
statut = du
Phase 7 — Saisie admin des paiements (à partir des tickets)
Pour chaque ligne du registre collecteur :

L’admin saisit :
date_collecte (ex: aujourd’hui à 09:30)
etal
ticket_numero (tapé)
montant (proposé automatiquement = montant_attendu)
Le système vérifie :
ticket existe, appartient au collecteur (via lot), statut = disponible
aucun paiement déjà lié
taxe du jour pour (date, etal) pas déjà payée
Le système enregistre dans une transaction atomique :
Paiement créé
Ticket passe à utilise, date_utilisation = date_collecte
TaxeJournaliere passe à paye (ou partiel)
Phase 8 — Contrôle “Qui n’a pas payé ?”
Sur la feuille du jour :

tous les étals occupés
ceux dont TaxeJournaliere.statut = du => non payés
retard = du et date < aujourd’hui
5) Contrôles anti-fraude indispensables (règles non négociables)
A) Ticket
1 ticket = 1 paiement (jamais réutilisable)
Ticket “utilisé” uniquement via création de paiement
Si un paiement est annulé, le ticket doit passer en :
soit annulé (recommandé), pas “redevenu disponible” (sinon recycle frauduleux)
ou redevenir disponible seulement si tu sais gérer un audit strict (plus risqué)
B) Carnet / Lot
Tous les tickets remis à un collecteur sont connus.
Tout ticket manquant doit être justifié.
C) Taxe journalière
Unique(date, etal)
Montant attendu calculé, pas tapé manuellement (sinon manipulation)
Montant payé peut être :
obligatoire = attendu (plus simple/anti-fraude)
ou partiel autorisé mais alors il faut contrôler strictement et tracer les restes
D) Audit
Tu as déjà AuditLog dans ton projet : il faut l’utiliser pour tracer :

création de paiements
annulation
modification ticket / lot
clôture de lot
6) Point important : ce que ton code actuel doit changer (pour suivre ce scénario)
Sans écrire le code ici, les changements incontournables sont :

Saisie paiement par numéro de ticket (pas dropdown limité)
Ticket.date_utilisation = date_collecte, pas timezone.now()
Empêcher ticket_update de mettre “utilisé” sans paiement
Ajouter la logique “LotTickets/Collecteur”
Ajouter TaxeJournaliere si taxe est journalière
7) Deux décisions à verrouiller (sinon scénario incomplet)
Réponds par “oui/non” à chaque :

Montant journalier doit être strictement le montant attendu (pas de partiel) ?
Si oui = anti-fraude maximal et reporting simple.
Si un paiement est annulé : tu veux que le ticket devienne annulé (recommandé) ou redevenir disponible ?