Voici le Plan Complet, l'Architecture Technique Row-Level, ainsi que le Prompt d'Ingénierie Clé en Main à copier-coller dans votre nouvelle discussion sur le
nouveau workspace.
──────
PARTIE 1 : PLAN GLOBAL & ARCHITECTURE ROW-LEVEL DU SAAS PHARMACIE

    ┌─────────────────────────────────────────────────────────────────────────────────────────────────┐
    │                                  SAAS PHARMACIE MULTI-TENANT (ROW-LEVEL)                        │
    ├─────────────────────────────────────────────────────────────────────────────────────────────────┤
    │ 1. IDENTIFICATION & TENANCY                                                                     │
    │    • Pharmacy (Tenant) ──< User (ADMIN/TITULAIRE, PHARMACIEN, CAISSIER, COMPTABLE)             │
    │                                                                                                 │
    │ 2. CATALOGUE UNIVERSEL & STOCKS PRIVÉS                                                         │
    │    • MedicamentCatalog (Global/Partagé) : Code-barres (EAN-13/CIP), Nom, DCI, Forme, Rayon     │
    │    • PharmacyProduct (Privé par pharmacie) : Prix Achat HT, Prix Vente, Seuil Alerte, Taux TVA│
    │    • ProductBatch/Lot (Lots & Péremptions) : Numéro Lot, Date Péremption, Quantité Disponible  │
    │                                                                                                 │
    │ 3. CAISSE & POINT DE VENTE (POS)                                                                │
    │    • CashSession (Par caissier, reset quotidien à 00:00, fonds initial, clôture & écart)       │
    │    • Sale (Ticket, Mode: ESPECE, WAVE, OMONEY, COMPTE_CLIENT, Statut: PAYE, CREDIT, ANNULE)    │
    │    • SaleItem (Produit, Quantité, Prix unitaire, Lot décrémenté en FEFO)                       │
    │                                                                                                 │
    │ 4. COMPTES CLIENTS & CRÉDITS (Acomptes / Fin de mois)                                           │
    │    • CustomerAccount : Solde, Plafond crédit autorisé, Type (PREPAYE / FACTURE_MENSUELLE)      │
    │    • CustomerTransaction : Crédit (+ dépôt acompte), Débit (- achat ticket), Solde après op   │
    │                                                                                                 │
    │ 5. FOURNISSEURS, COMMANDES & IMPORT/EXPORT CSV                                                  │
    │    • Supplier : Nom, Téléphone, Email, Délai livraison, Adresse                                │
    │    • PurchaseOrder : Génération proposition selon ventes (Jour/Semaine), Export CSV            │
    │    • StockReception : Import CSV fournisseur ou saisie directe, mise à jour des lots           │
    │    • SupplierClaim (Réclamation) : Type (EXPIRÉ, MANQUANT, ERREUR_PRODUIT), Photo, Motif       │
    │                                                                                                 │
    │ 6. DÉPENSES & ÉTAT FINANCIER CONSOLIDÉ                                                          │
    │    • ExpenseCategory & Expense : Dépenses d'exploitation, Justificatif                         │
    │    • FinancialReportService : Total Ventes - Total Dépenses = Solde Net & Marge Brute          │
    └─────────────────────────────────────────────────────────────────────────────────────────────────┘

──────
PARTIE 2 : SPÉCIFICATION DÉTAILLÉE DES MODÈLES & FLUX MÉTIER

### 1. Analyse du format CSV existant (export-stocks-\*.csv)

Le modèle de données intègre nativement toutes les colonnes de votre export actuel :

• Code 1 & Code 2 → barcode & alternate_barcode (Index B-Tree pour recherche instantanée au scan).
• Code géo → shelf_location (Rayon/Emplacement physique dans l'officine).
• Label → name & form_dosage.
• Prix unitaire d'achat HT → purchase_price_ht.
• Prix unitaire de vente → selling_price.
• Date de péremption la plus proche → expiration_date du premier lot.

### 2. Alertes Péremption dans les Réponses JSON

Chaque produit retourné par l'API inclut des champs calculés dynamiquement pour le frontend :

• is_expiring_soon : true si le lot le plus proche expire dans moins de 3 mois.
• months_until_expiry : nombre de mois restants.
• is_low_stock : true si stock_total <= seuil_alerte.

### 3. Gestion des Comptes Clients (Acomptes & Crédits)

• Client avec Solde (ex: 50 000 FCFA) : Lors de la vente, le mode COMPTE_CLIENT débite le compte en temps réel (solde_restant). L'API renvoie le solde actualisé et
le statut (ex: solde_suffisant ou depassement_plafond).
• Clients conventionnés / Fin de mois : Permet la vente à crédit avec état récapitulatif des factures impayées téléchargeable en fin de mois.

### 4. Cycle de Commande & Réclamations Fournisseurs

1. Proposition de commande automatique : L'admin clique sur "Générer commande" → Le système sélectionne tous les produits vendus sur la période (Jour/Semaine) ayant
   atteint leur seuil critique.
2. Export CSV : Export propre au format attendu par le portail du grossiste (ex: Laborex, Cophase...).
3. Import CSV Réception : À la livraison, le pharmacien importe le bon de livraison CSV → Mise à jour automatique des quantités et enregistrement des nouveaux
   numéros de lots et dates de péremption.
4. Réclamation liée à la commande : En cas d'erreur de livraison (produit périmé, cassé ou manquant), création d'un ticket de réclamation lié au fournisseur et au
   numéro de commande avec description et photo justificative.
   ──────
   PARTIE 3 : PROMPT D'INGÉNIERIE COMPLET POUR LE NOUVEAU WORKSPACE

(Copiez-collez l'intégralité du texte ci-dessous dans la première invite de votre nouveau projet)

    # CONTEXTE & OBJECTIF DU PROJET

    Nous construisons un **SaaS de Gestion Intégrale d'Officine de Pharmacie et Point de Vente (POS)** 100% en Français.

    ## 1. PRINCIPES ARCHITECTURAUX FONDAMENTAUX
    1. **Architecture Multi-Tenant :** Approche **Row-Level Tenancy** (Base de données partagée avec isolation stricte par `pharmacy_id` sur tous les modèles privés).
    2. **Simplicité Maximale du Code :** Zéro tâche de fond (Pas de Celery / Pas de workers asynchrones). Tous les calculs financiers, alertes de péremption et

déstockages sont effectués de façon synchrone et transactionnelle (`transaction.atomic`). 3. **Optimisé pour Caisse POS :** Temps de réponse < 50ms sur les recherches par code-barres (EAN-13, CIP), gestion des douchettes USB/Bluetooth (sans focus
obligatoire), compatibilité impression ticket thermique 80mm/58mm via CSS `@media print` et ouverture de tiroir-caisse RJ11. 4. **Stack Technique :** - **Backend :** Django 6.0+ / Python 3.12 + Django REST Framework + SimpleJWT + PostgreSQL. - **Frontend :** React (Vite) + Tailwind CSS + Lucide Icons.

    ---

    ## 2. MODÈLES DE DONNÉES ET STRUCTURE RELATIONNELLE

    ### A. Tenancy & Utilisateurs
    - `Pharmacy` : `id`, `name`, `license_number`, `phone`, `address`, `city`, `logo`, `created_at`, `is_active`.
    - `User` (Custom User hérité d'AbstractUser) :
      - Champs : `pharmacy` (ForeignKey), `phone`, `role` (`ADMIN`/`TITULAIRE`, `PHARMACIEN`, `CAISSIER`, `COMPTABLE`).

    ### B. Catalogue Global & Stocks Privés
    - `MedicamentCatalog` (Catalogue national partagé) :
      - `barcode` (EAN-13/CIP, unique, indexé), `name`, `dci`, `form_dosage`, `default_category`.
    - `PharmacyProduct` (Produit privé de l'officine) :
      - `pharmacy` (FK), `catalog_item` (FK optionnelle), `barcode` (Index B-Tree), `alternate_barcode`, `name`, `shelf_location` (Rayon/Code géo),

`purchase_price_ht`, `selling_price`, `tva_rate`, `reorder_threshold`, `is_active`. - `ProductBatch` (Lots & Périssabilité - Modèle FEFO) : - `pharmacy` (FK), `product` (FK), `batch_number`, `expiration_date`, `quantity_received`, `quantity_current`. - Propriétés JSON calculées : `is_expiring_soon` (si expiration < 90 jours), `months_until_expiry`, `is_expired`.

    ### C. Caisse POS & Ventes
    - `CashSession` (Session de Caisse quotidienne) :
      - `pharmacy` (FK), `cashier` (FK User), `session_date`, `opened_at`, `closed_at`, `initial_cash` (Fonds de caisse), `expected_cash`, `actual_cash_counted`,

`cash_difference`, `status` (`OPEN`, `CLOSED`). - Règle métier : Une session est automatiquement ouverte par caissier le matin, et réinitialisée à 00:00. - `Sale` (Ticket de caisse) : - `pharmacy` (FK), `cash_session` (FK), `cashier` (FK User), `ticket_number` (ex: `VTE-YYYYMMDD-XXXX`), `customer` (FK CustomerAccount optionnelle), `total_ht`,
`total_ttc`, `payment_method` (`ESPECE`, `WAVE`, `OMONEY`, `COMPTE_CLIENT`, `MIXTE`), `status` (`PAID`, `CREDIT`, `CANCELLED`), `created_at`. - `SaleItem` : - `sale` (FK), `product` (FK), `batch` (FK ProductBatch), `quantity`, `unit_price`, `total_price`. - Logique de déstockage : Décrémente automatiquement le lot dont la date de péremption est la plus proche (FEFO).

    ### D. Comptes Clients & Ventes à Crédit / Acomptes
    - `CustomerAccount` :
      - `pharmacy` (FK), `name`, `phone`, `email`, `account_type` (`PREPAID` avec acompte, `CREDIT_MONTHLY` paiement fin de mois), `current_balance` (positif =

acompte dispo, négatif = dette), `credit_limit` (plafond autorisé). - `CustomerTransaction` : - `customer` (FK), `sale` (FK optionnelle), `transaction_type` (`DEPOSIT`, `PURCHASE`, `REFUND`), `amount`, `balance_after`, `note`, `created_at`.

    ### E. Fournisseurs, Commandes & Réclamations
    - `Supplier` :
      - `pharmacy` (FK), `name`, `phone`, `email`, `address`, `contact_person`, `order_website_url`.
    - `PurchaseOrder` :
      - `pharmacy` (FK), `supplier` (FK), `order_number` (ex: `CMD-YYYYMMDD-XXX`), `status` (`DRAFT`, `EXPORTED`, `RECEIVED`, `CANCELLED`), `notes`, `created_at`.
    - `PurchaseOrderItem` :
      - `order` (FK), `product` (FK), `quantity_ordered`, `quantity_received`, `unit_purchase_price`.
    - `SupplierClaim` (Réclamation Fournisseur) :
      - `pharmacy` (FK), `supplier` (FK), `order` (FK PurchaseOrder optionnelle), `claim_type` (`EXPIRED_RECEIVED`, `MISSING_ITEM`, `WRONG_PRODUCT`, `DAMAGED`),

`product_name`, `batch_number`, `quantity_affected`, `description`, `photo_proof`, `status` (`PENDING`, `ACCEPTED`, `REFUNDED`, `REJECTED`), `created_at`.

    ### F. Dépenses & États Financiers
    - `ExpenseCategory` : `pharmacy` (FK), `name` (Loyer, Électricité, Salaires, Fournitures...).
    - `Expense` : `pharmacy` (FK), `category` (FK), `amount`, `payment_method` (`ESPECE`, `WAVE`, `OMONEY`), `description`, `receipt_file`, `date`, `created_by`.

    ---

    ## 3. FONCTIONNALITÉS CLÉS & ENDPOINTS API REQUIS

    1. **Import/Export Stock CSV :**
       - Endpoint `POST /api/pharmacy/inventory/import-csv/` capable de parser le format CSV existant (`Code 1`, `Code 2`, `Code géo`, `Label`, `Quantité`, `Prix

unitaire d'achat HT`, `Prix unitaire de vente`, `Date de péremption la plus proche`).
       - Endpoint `GET /api/pharmacy/inventory/export-csv/`.
    2. **Génération de Commande Fournisseur :**
       - Endpoint `POST /api/pharmacy/orders/generate-from-sales/?period=today|week`: analyse les ventes et les ruptures pour générer un fichier CSV prêt à être
  importé sur le site du fournisseur.
       - Endpoint`POST /api/pharmacy/orders/{id}/import-delivery-csv/`: met à jour automatiquement le stock et crée les lots avec leurs dates de péremption lors de
  la livraison.
    3. **Scan Barcode Caisse POS :**
       - Endpoint`GET /api/pharmacy/pos/scan/?barcode=XXXXX`: renvoie les données produit, le prix et les lots disponibles avec indicateur`is_expiring_soon`en <
  20ms.
    4. **Encaissement & Validation Vente :**
       - Endpoint`POST /api/pharmacy/pos/checkout/`: validation atomique du ticket, décrémentation des lots FEFO, mise à jour de la session de caisse et débit du
  compte client le cas échéant.
    5. **Session de Caisse :**
       -`POST /api/pharmacy/pos/session/open/`&`POST /api/pharmacy/pos/session/close/`avec calcul des écarts d'espèces.
    6. **État Financier Consolidé :**
       -`GET /api/pharmacy/financial-statement/?period=today|week|month|custom&payment_method=ESPECE|WAVE|OMONEY`       - Calcule :`total_ventes`, `total_depenses`, `solde_net`, `marge_brute_estimee`, `ventilation_modes_paiement`.

    ---

    ## 4. INSTRUCTIONS D'EXÉCUTION
    - RLS + contraintes PostgreSQL + permissions Django
    - Mettre en place la base de code Django 6.0+ propre et modulaire.
    - Utiliser des ViewSets DRF sécurisés avec filtrage strict `RLS + contraintes PostgreSQL + permissions Django`.
    - Le tenant_id ne doit jamais etre 1,2,3 trop facile a deviner mais unique e de la facon (MT6509457A)
    - Documenter le format JSON de chaque endpoint avec OpenAPI / drf-spectacular.
