# PharmaBack — SaaS de Gestion Intégrale d'Officine & Point de Vente (POS)

Système de gestion d'officine pharmaceutique et de caisse POS multi-tenant basé sur **Django 6.0+**, **Django REST Framework (DRF)**, **SimpleJWT**, et **PostgreSQL 16+ avec Row-Level Security (RLS)**.

---

## 🛡️ Architecture Multi-Tenant & Sécurité PostgreSQL RLS

L'isolation des données repose sur **PostgreSQL Row-Level Security (RLS)** couplée à un filtrage au niveau de l'ORM (Défense en profondeur) :

1. **Format Identifiant Officine (Tenant ID) :** Format sécurisé `MTXXXXXXXL` (ex: `MT4920194K`).
2. **Transaction-Scoped Context :** Utilisation stricte de `SET LOCAL app.current_tenant_id = '...'` dans chaque transaction de requête HTTP et tâche backend via [`TransactionalTenantRLSMiddleware`](file:///home/khalipha/thiane/repos/Pharmaback/tenancy/middleware.py).
3. **Modèle de Base Abstrait :** [`TenantModel`](file:///home/khalipha/thiane/repos/Pharmaback/tenancy/models.py) empêchant toute altération de l'`officine_id` après création et imposant les contraintes d'intégrité relationnelle multi-tenant.
4. **Politiques RLS Automatiques :** Migrations PostgreSQL avec clauses `USING` et `WITH CHECK` sur tous les modèles privés.

---

## 💼 Gestion des Abonnements SaaS (Plan Unique Pro)

- **Gestion Manuelle par le Propriétaire SaaS :** Pas de passerelle de paiement en ligne ; le SuperAdmin / Propriétaire de la plateforme active, prolonge ou suspend manuellement les abonnements des officines.
- **Plan Unique :** `PLAN UNIQUE PRO` (30 000 FCFA / mois) couvrant tous les modules (POS, Stocks FEFO, Comptes Clients, Fournisseurs et États Financiers).
- **Vérification en Temps Réel :** [`SubscriptionCheckMiddleware`](file:///home/khalipha/thiane/repos/Pharmaback/tenancy/middleware.py) verrouille l'accès aux endpoints de l'officine lorsque l'abonnement expire ou est suspendu (HTTP 403 `SUBSCRIPTION_REQUIRED`).

---

## 📦 Modules & Fonctionnalités Clés

### 1. Tenancy & Authentification ([`apps/authentication`](file:///home/khalipha/thiane/repos/Pharmaback/apps/authentication/models.py))
- Utilisateur personnalisé avec rôles : `SAAS_OWNER`, `ADMIN` (Titulaire), `PHARMACIEN`, `CAISSIER`, `COMPTABLE`.
- Jetons SimpleJWT enrichis avec claims d'officine (`tenant_id`, `pharmacy_name`, `role`, `subscription_status`).

### 2. Catalogue Global & Stocks Privés FEFO ([`apps/inventory`](file:///home/khalipha/thiane/repos/Pharmaback/apps/inventory/models.py))
- **Catalogue National Partagé :** [`MedicamentCatalog`](file:///home/khalipha/thiane/repos/Pharmaback/apps/catalog/models.py) pour recherche globale CIP/EAN-13.
- **Produits Privés & Lots :** [`PharmacyProduct`](file:///home/khalipha/thiane/repos/Pharmaback/apps/inventory/models.py) et [`ProductBatch`](file:///home/khalipha/thiane/repos/Pharmaback/apps/inventory/models.py) suivant le principe FEFO (First Expired, First Out).
- **Import/Export CSV de Stock :** Parser compatible avec le format existant (`Code 1`, `Code 2`, `Code géo`, `Label`, `Quantité`, `Prix unitaire d'achat HT`, `Prix unitaire de vente`, `Date de péremption la plus proche`).
- **Indicateurs Calculés :** `is_expiring_soon` (< 90 jours), `months_until_expiry`, `is_low_stock` (`total_stock <= reorder_threshold`).

### 3. Point de Vente (POS) & Caisse ([`apps/pos`](file:///home/khalipha/thiane/repos/Pharmaback/apps/pos/models.py))
- **Scan Ultra-Rapide (< 20ms) :** `GET /api/pharmacy/pos/scan/?barcode=XXXXX`.
- **Sessions de Caisse Quotidiennes :** [`CashSession`](file:///home/khalipha/thiane/repos/Pharmaback/apps/pos/models.py) avec fonds initial, clôture et calcul automatique des écarts d'espèces (`cash_difference`).
- **Encaissement Atomique :** `POST /api/pharmacy/pos/checkout/` décrémentant les lots FEFO, créant le ticket de caisse et traçant les mouvements de stock.

### 4. Comptes Clients & Crédits ([`apps/customers`](file:///home/khalipha/thiane/repos/Pharmaback/apps/customers/models.py))
- **Acomptes & Facturation Fin de Mois :** [`CustomerAccount`](file:///home/khalipha/thiane/repos/Pharmaback/apps/customers/models.py) avec contrôle du plafond de crédit (`credit_limit`).
- **Relevé Mensuel :** `GET /api/pharmacy/customers/{id}/statement/`.

### 5. Fournisseurs, Commandes & Réclamations ([`apps/suppliers`](file:///home/khalipha/thiane/repos/Pharmaback/apps/suppliers/models.py))
- **Proposition de Commande Automatique :** `POST /api/pharmacy/orders/generate-from-sales/?period=today|week` analysant les ventes et ruptures de stock.
- **Réception Bon de Livraison CSV :** `POST /api/pharmacy/orders/{id}/import-delivery-csv/` intégrant automatiquement les nouveaux lots et dates de péremption.
- **Réclamations Grossistes :** [`SupplierClaim`](file:///home/khalipha/thiane/repos/Pharmaback/apps/suppliers/models.py) avec photo justificative (`DAMAGED`, `EXPIRED_RECEIVED`, `MISSING_ITEM`).

### 6. Dépenses & État Financier Consolidé ([`apps/billing`](file:///home/khalipha/thiane/repos/Pharmaback/apps/billing/models.py))
- **Dépenses d'Exploitation :** [`Expense`](file:///home/khalipha/thiane/repos/Pharmaback/apps/billing/models.py) par catégorie avec pièces jointes.
- **Bilan Consolidé :** `GET /api/pharmacy/financial-statement/?period=today|week|month|custom` :
  - `total_ventes_ttc`, `total_ventes_ht`, `total_tva_collectee`
  - `total_depenses`, `solde_net` (Cashflow)
  - `cout_achat_marchandises`, `marge_brute_estimee`, `taux_marge_pourcentage`
  - `ventilation_modes_paiement` (Espèces, Wave, Orange Money, Compte Client...)
  - `creances_clients_total` & `acomptes_clients_total`

---

## 🚀 Démarrage & Installation

### 1. Cloner et configurer l'environnement
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Appliquer les migrations PostgreSQL RLS
```bash
python manage.py migrate
```

### 3. Lancer la suite de tests
```bash
python manage.py test tests
```

### 4. Lancer le serveur de développement
```bash
python manage.py runserver
```

---

## 📚 Documentation OpenAPI 3.0 & Swagger

- **Swagger UI :** [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)
- **ReDoc :** [http://localhost:8000/api/redoc/](http://localhost:8000/api/redoc/)
- **Schéma OpenAPI JSON/YAML :** [http://localhost:8000/api/schema/](http://localhost:8000/api/schema/)
