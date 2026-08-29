# PLAN D'ARCHITECTURE FRONTEND & PROMPT D'INGÉNIERIE CLÉ EN MAIN
## SaaS Gestion d'Officine de Pharmacie & Caisse POS (100% Français)

---

# PARTIE 1 : ARCHITECTURE TECHNIQUE & GUIDE D'IMPLÉMENTATION DU FRONTEND

### 1. Stack Technique & Principes Directeurs
- **Framework :** React 19 / 18+ (Vite) + TypeScript + React Compiler + ESLint.
- **Styling :** Tailwind CSS + Lucide Icons + Fonts (`Inter` / `Geist` / `JetBrains Mono` pour les tickets).
- **Gestion d'État & API :** TanStack Query v5 (React Query) pour le cache serveur, Zustand pour le panier POS et la session active.
- **Routage :** React Router DOM v6/v7 avec Layouts différenciés (SaaS Admin vs Officine).
- **Design System Modulaire (UI-First) :** 100% Component-Driven. Aucun bouton, champ de saisie, carte de statistique, badge ou modal n'est écrit en dur (Atomic Design : `Button`, `Input`, `Select`, `Card`, `StatCard`, `Badge`, `Modal`, `DataTable`, `Drawer`, `BottomNav`, `Sidebar`).
- **Responsive :** Mobile-First avec Bottom Navigation Bar sur smartphone/tablette et Sidebar collapsible sur Desktop.
- **Impression Thermique & PDF :** `@media print` CSS optimisé pour tickets 80mm/58mm et `jsPDF` / `@react-pdf/renderer` pour les factures A4 générées à la demande.

---

### 2. Arborescence du Projet Frontend

```
pharmaback-frontend/
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── TODO.md                         # Suivi d'avancement des tâches
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── routes/                     # Configuration des routes
│   │   ├── index.tsx
│   │   ├── ProtectedRoute.tsx
│   │   └── RoleGuard.tsx
│   ├── layouts/
│   │   ├── AuthLayout.tsx          # Login & Déconnexion
│   │   ├── PharmacyLayout.tsx      # Sidebar (Desktop) + BottomNav (Mobile)
│   │   └── SaasOwnerLayout.tsx     # Console Propriétaire SaaS
│   ├── components/
│   │   ├── ui/                     # Design System Réutilisable (Zéro hardcoding)
│   │   │   ├── Button.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Select.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── StatCard.tsx
│   │   │   ├── Badge.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Drawer.tsx
│   │   │   ├── DataTable.tsx
│   │   │   ├── SearchInput.tsx
│   │   │   └── Toast.tsx
│   │   ├── navigation/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── BottomNav.tsx
│   │   │   └── Navbar.tsx
│   │   ├── pos/                    # Composants Caisse
│   │   │   ├── BarcodeScannerModal.tsx # Scanner Caméra Mobile
│   │   │   ├── PosCart.tsx
│   │   │   ├── PaymentModal.tsx    # Espèce (rendu monnaie), Wave, OM, Compte
│   │   │   └── ThermalReceipt.tsx  # Ticket thermique 80mm/58mm
│   │   ├── inventory/
│   │   │   ├── ExpiryAlertBadge.tsx
│   │   │   ├── StockImportModal.tsx
│   │   │   └── QuickOrderModal.tsx # Commande express stock < 2
│   │   └── print/
│   │       └── InvoicePdfDocument.tsx # Facture PDF officielle à la demande
│   ├── services/                   # API Client & Axios Interceptors
│   │   ├── api.ts
│   │   ├── auth.service.ts
│   │   ├── tenancy.service.ts
│   │   ├── catalog.service.ts
│   │   ├── inventory.service.ts
│   │   ├── pos.service.ts
│   │   ├── customers.service.ts
│   │   ├── suppliers.service.ts
│   │   └── billing.service.ts
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useBarcodeScanner.ts    # Détection douchette USB Desktop
│   │   ├── useCameraScanner.ts     # Caméra mobile avec permission persistante
│   │   └── useThermalPrinter.ts
│   ├── stores/
│   │   ├── authStore.ts
│   │   ├── posCartStore.ts
│   │   └── cashSessionStore.ts
│   ├── types/                      # Typage TypeScript strict
│   │   ├── auth.types.ts
│   │   ├── inventory.types.ts
│   │   ├── pos.types.ts
│   │   ├── customer.types.ts
│   │   ├── supplier.types.ts
│   │   ├── billing.types.ts
│   │   └── tenancy.types.ts
│   └── views/
│       ├── auth/
│       │   └── LoginView.tsx       # Support URL bookmarkable ?tenant=MTXXXXXXXL
│       ├── saas/                   # Espace Propriétaire SaaS Exclusif
│       │   ├── SaasDashboardView.tsx
│       │   ├── SaasTenantsView.tsx
│       │   └── SaasCatalogView.tsx
│       └── pharmacy/               # Espace Officine (Zéro suppression autorisée)
│           ├── dashboard/
│           │   └── PharmacyDashboardView.tsx
│           ├── pos/
│           │   ├── PosView.tsx     # Caisse tactile ultra-rapide
│           │   ├── CashSessionsView.tsx
│           │   └── SalesHistoryView.tsx
│           ├── inventory/
│           │   ├── StockListView.tsx # Alerte péremption rouge (< 3 mois)
│           │   ├── ProductFormView.tsx
│           │   └── StockMovementsView.tsx
│           ├── customers/
│           │   ├── CustomerAccountsView.tsx
│           │   └── CustomerStatementView.tsx
│           ├── suppliers/
│           │   ├── SupplierOrdersView.tsx
│           │   ├── DeliveryImportView.tsx
│           │   └── SupplierClaimsView.tsx
│           ├── billing/
│           │   ├── ExpensesView.tsx
│           │   └── FinancialStatementView.tsx
│           └── settings/
│               ├── TeamManagementView.tsx # 3 options de mot de passe
│               └── PharmacyProfileView.tsx
```

---

# PARTIE 2 : CONTRATS D'INTERFACE API COMPLETS (ROUTES, JSON REQUEST & RESPONSE)

> **Règle de sécurité multi-tenant :** Le `tenant_id` n'est **jamais** envoyé dans le body des requêtes. Il est extrait directement du JWT décodé côté serveur et côté client.

---

### 1. Authentification & Connexion

#### `POST /api/auth/login/`
- **Description :** Connexion utilisateur (SaaS Owner ou Staff d'Officine).
- **Body JSON :**
```json
{
  "username": "caissier_fatou",
  "password": "StrongPassword123!"
}
```
- **Response JSON (200 OK) :**
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 2,
    "username": "caissier_fatou",
    "email": "fatou@pharma.sn",
    "role": "CAISSIER",
    "phone": "771234567",
    "is_superuser": false,
    "pharmacy": {
      "id": "MT4829104K",
      "name": "Grande Pharmacie Dakar",
      "code": "pharma_dakar",
      "is_active": true
    }
  },
  "subscription": {
    "status": "ACTIVE",
    "end_date": "2026-09-26T12:00:00Z",
    "is_valid": true
  }
}
```

#### `GET /api/auth/profile/`
- **Response JSON (200 OK) :**
```json
{
  "id": 2,
  "username": "caissier_fatou",
  "email": "fatou@pharma.sn",
  "first_name": "Fatou",
  "last_name": "Sow",
  "phone": "771234567",
  "role": "CAISSIER",
  "pharmacy": {
    "id": "MT4829104K",
    "name": "Grande Pharmacie Dakar",
    "code": "pharma_dakar",
    "license_number": "LIC-SN-001",
    "phone": "338210000",
    "address": "12 Avenue Ponty",
    "city": "Dakar",
    "logo": null,
    "is_active": true
  },
  "is_active": true,
  "date_joined": "2026-08-26T09:00:00Z"
}
```

#### `GET /api/pharmacy/subscription/status/`
- **Response JSON (200 OK) :**
```json
{
  "id": 1,
  "tenant": "MT4829104K",
  "plan": 1,
  "plan_details": {
    "name": "PLAN UNIQUE PRO",
    "price": "30000.00",
    "duration_days": 30
  },
  "status": "ACTIVE",
  "start_date": "2026-08-26T00:00:00Z",
  "end_date": "2026-09-26T00:00:00Z",
  "is_active": true,
  "is_valid": true,
  "notes": "Abonnement actif."
}
```

---

### 2. Propriétaire SaaS (Plateforme & Abonnements)

#### `GET /api/saas/tenants/`
- **Response JSON (200 OK) :**
```json
[
  {
    "id": "MT4829104K",
    "name": "Grande Pharmacie Dakar",
    "code": "pharma_dakar",
    "license_number": "LIC-SN-001",
    "phone": "338210000",
    "city": "Dakar",
    "is_active": true,
    "subscription": {
      "id": 1,
      "status": "ACTIVE",
      "start_date": "2026-08-26T00:00:00Z",
      "end_date": "2026-09-26T00:00:00Z",
      "is_valid": true
    }
  }
]
```

#### `POST /api/saas/tenants/` (Création Atomique : Officine + Abonnement + Titulaire)
- **Description :** Permet au Propriétaire SaaS d'enregistrer une nouvelle officine tout en créant instantanément son compte Titulaire (Pharmacy Owner) et son abonnement.
- **Body JSON :**
```json
{
  "name": "Pharmacie du Plateau",
  "code": "pharma_plateau",
  "license_number": "LIC-SN-002",
  "phone": "338220000",
  "address": "Place de l'Indépendance",
  "city": "Dakar",
  "initial_duration_days": 30,
  "initial_status": "ACTIVE",
  "owner": {
    "username": "dr_diop",
    "email": "diop@pharma.sn",
    "first_name": "Cheikh",
    "last_name": "Diop",
    "phone": "771234567",
    "auto_generate_password": true
  }
}
```
- **Response JSON (201 Created) :**
```json
{
  "id": "MT4829104K",
  "name": "Pharmacie du Plateau",
  "code": "pharma_plateau",
  "license_number": "LIC-SN-002",
  "phone": "338220000",
  "address": "Place de l'Indépendance",
  "city": "Dakar",
  "logo": null,
  "is_active": true,
  "created_at": "2026-08-26T12:00:00Z",
  "subscription": {
    "id": 1,
    "status": "ACTIVE",
    "start_date": "2026-08-26T12:00:00Z",
    "end_date": "2026-09-25T12:00:00Z",
    "is_valid": true
  },
  "owner": {
    "id": 3,
    "username": "dr_diop",
    "email": "diop@pharma.sn",
    "first_name": "Cheikh",
    "last_name": "Diop",
    "phone": "771234567",
    "role": "ADMIN",
    "generated_password": "Pharma@k9xL2p8Q"
  }
}
```

#### `POST /api/saas/tenants/{id}/create-owner/` (Ajout/Réinitialisation du Titulaire pour une Officine existante)
- **Body JSON :**
```json
{
  "username": "nouveau_titulaire",
  "email": "titulaire@pharma.sn",
  "first_name": "Ousmane",
  "last_name": "Ba",
  "phone": "773334455",
  "auto_generate_password": true
}
```
- **Response JSON (201 Created) :**
```json
{
  "status": "success",
  "message": "Compte Titulaire créé avec succès pour l'officine Pharmacie du Plateau.",
  "owner": {
    "id": 4,
    "username": "nouveau_titulaire",
    "email": "titulaire@pharma.sn",
    "first_name": "Ousmane",
    "last_name": "Ba",
    "phone": "773334455",
    "role": "ADMIN",
    "pharmacy_id": "MT4829104K",
    "generated_password": "Pharma@a8Z9xQ2P"
  }
}
```

#### `POST /api/saas/tenants/{id}/extend-subscription/`
- **Body JSON :**
```json
{
  "days": 60
}
```

---

### 3. Répertoire National des Médicaments (`/api/catalog/`)
Base de référence commune à toutes les officines (3 991 références). Sans prix ni quantité (propres aux officines).

#### `GET /api/catalog/` (Recherche Médicament National)
- **Query Params :**
  - `?search=4042809000733` *(Recherche par Code 1, Code 2, Code géo ou Nom)*
  - `?ordering=name`
- **Response JSON (200 OK) :**
```json
[
  {
    "id": 1,
    "barcode": "4042809000733",
    "alternate_barcode": "4042809000733",
    "geo_code": "CH",
    "name": "BANDE HYPAFIX ADH 10M X10",
    "dci": "",
    "form_dosage": "",
    "default_category": "",
    "is_active": true
  },
  {
    "id": 2,
    "barcode": "8436024611748",
    "alternate_barcode": "8436024612615",
    "geo_code": "RAYON AMPOULE",
    "name": "POTENCIATOR 5G AMP BUV B/20",
    "dci": "",
    "form_dosage": "",
    "default_category": "",
    "is_active": true
  }
]
```

#### `POST /api/catalog/` (Ajout Médicament - SaaS Owner Uniquement)
- **Body JSON :**
```json
{
  "barcode": "8436024611748",
  "alternate_barcode": "8436024612615",
  "geo_code": "RAYON AMPOULE",
  "name": "POTENCIATOR 5G AMP BUV B/20"
}
```
*(Remarque : `default_category`, `dci`, `form_dosage` et `alternate_barcode` sont optionnels).*
- **Response JSON (201 Created) :**
```json
{
  "id": 2,
  "barcode": "8436024611748",
  "alternate_barcode": "8436024612615",
  "geo_code": "RAYON AMPOULE",
  "name": "POTENCIATOR 5G AMP BUV B/20",
  "dci": "",
  "form_dosage": "",
  "default_category": "",
  "is_active": true,
  "created_at": "2026-08-27T18:00:00Z",
  "updated_at": "2026-08-27T18:00:00Z"
}
```

---

### 4. Gestion de l'Équipe d'Officine (Par le Titulaire)

#### `POST /api/auth/users/`
- **Option 1 & 2 (Mot de passe généré ou saisi sur place) :**
```json
{
  "username": "pharmacien_ali",
  "email": "ali@pharma.sn",
  "password": "GeneratedOrGivenPass123!",
  "first_name": "Ali",
  "last_name": "Fall",
  "phone": "775550011",
  "role": "PHARMACIEN",
  "is_active": true
}
```

---

### 5. Stock, Produits & Alertes Péremption

#### `GET /api/pharmacy/inventory/products/?low_stock=true|false&expiring_soon=true|false&search=Doliprane`
- **Response JSON (200 OK) :**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "barcode": "3400930000010",
      "alternate_barcode": "CIP10",
      "name": "Doliprane 1000mg Comprimés",
      "shelf_location": "RAYON-A1",
      "purchase_price_ht": "1000.00",
      "selling_price": "1500.00",
      "tva_rate": "0.00",
      "reorder_threshold": 15,
      "is_active": true,
      "total_stock": 8,
      "is_low_stock": true,
      "is_expiring_soon": true,
      "months_until_expiry": 2,
      "nearest_expiration_date": "2026-10-31",
      "batches": [
        {
          "id": 1,
          "batch_number": "LOT-202610-0010",
          "expiration_date": "2026-10-31",
          "quantity_received": 50,
          "quantity_current": 8,
          "is_expiring_soon": true,
          "months_until_expiry": 2,
          "is_expired": false
        }
      ]
    }
  ]
}
```

#### `POST /api/pharmacy/inventory/products/`
- **Body JSON :**
```json
{
  "barcode": "3400930000088",
  "alternate_barcode": "CIP88",
  "name": "Amoxicilline 500mg Gélules",
  "shelf_location": "RAYON-B3",
  "purchase_price_ht": "1200.00",
  "selling_price": "1800.00",
  "tva_rate": "0.00",
  "reorder_threshold": 10
}
```

#### `POST /api/pharmacy/inventory/products/quick-restock/` (Réapprovisionnement Express Unitaire)
- **Description :** Permet de réapprovisionner un produit en scannant son code-barres principal (`barcode`) OU son code alternatif (`alternate_barcode`), en saisissant simplement la nouvelle quantité reçue. Met à jour instantanément le stock disponible et crée le lot FEFO.
- **Body JSON :**
```json
{
  "barcode": "3400930000010",
  "quantity": 25,
  "batch_number": "LOT-202706-0010",
  "expiration_date": "2027-06-30",
  "purchase_price_ht": "1050.00",
  "selling_price": "1550.00"
}
```
*(Remarque : `batch_number`, `expiration_date`, `purchase_price_ht` et `selling_price` sont tous optionnels. Si omis, le lot est auto-généré et les prix existants sont conservés).*
- **Response JSON (200 OK) :**
```json
{
  "id": 1,
  "barcode": "3400930000010",
  "alternate_barcode": "CIP10",
  "name": "Doliprane 1000mg Comprimés",
  "shelf_location": "RAYON-A1",
  "purchase_price_ht": "1050.00",
  "selling_price": "1550.00",
  "total_stock": 33,
  "is_low_stock": false,
  "is_expiring_soon": false,
  "months_until_expiry": 10,
  "nearest_expiration_date": "2026-10-31",
  "batches": [
    {
      "id": 1,
      "batch_number": "LOT-202610-0010",
      "expiration_date": "2026-10-31",
      "quantity_current": 8
    },
    {
      "id": 2,
      "batch_number": "LOT-202706-0010",
      "expiration_date": "2027-06-30",
      "quantity_current": 25
    }
  ]
}
```

#### `POST /api/pharmacy/inventory/import-csv/`
- **Request Form-Data :** `file: export-stocks.csv`
- **Response JSON (200 OK) :**
```json
{
  "status": "success",
  "message": "Fichier CSV importé avec succès.",
  "created_products": 45,
  "updated_products": 12,
  "batches_created": 45,
  "errors_count": 0
}
```

#### `GET /api/pharmacy/inventory/export-csv/`
- **Response :** Fichier CSV binaire formaté avec séparateur `;`.

---

### 6. Point de Vente (POS), Sessions de Caisse & Ventes

#### `GET /api/pharmacy/pos/top-products/` (Les 10 Produits Phares - Quick-Add POS)
- **Response JSON (200 OK) :**
```json
[
  {
    "id": 1,
    "barcode": "3400930000010",
    "alternate_barcode": "CIP10",
    "name": "Doliprane 1000mg Comprimés",
    "shelf_location": "RAYON-A1",
    "selling_price": "1500.00",
    "total_stock": 48,
    "is_low_stock": false,
    "is_expiring_soon": false,
    "total_units_sold": 340
  },
  {
    "id": 2,
    "barcode": "3400930000030",
    "alternate_barcode": "CIP30",
    "name": "Efferalgan 1g Effervescent",
    "shelf_location": "RAYON-A2",
    "selling_price": "1400.00",
    "total_stock": 25,
    "is_low_stock": false,
    "is_expiring_soon": false,
    "total_units_sold": 215
  }
]
```

#### `GET /api/pharmacy/pos/scan/?barcode=3400930000010` (Temps < 20ms)
- **Response JSON (200 OK) :**
```json
{
  "id": 1,
  "barcode": "3400930000010",
  "alternate_barcode": "CIP10",
  "name": "Doliprane 1000mg Comprimés",
  "shelf_location": "RAYON-A1",
  "selling_price": "1500.00",
  "total_stock": 8,
  "is_low_stock": true,
  "is_expiring_soon": true,
  "months_until_expiry": 2,
  "nearest_expiration_date": "2026-10-31"
}
```

#### `GET /api/pharmacy/pos/session/current/` (Vérification d'état de la caisse)
- **Response JSON si caisse fermée (200 OK) :**
```json
{
  "has_open_session": false,
  "detail": "Aucune session ouverte actuellement."
}
```
- **Response JSON si caisse ouverte (200 OK) :**
```json
{
  "has_open_session": true,
  "id": 12,
  "cashier": 3,
  "cashier_username": "caissier_fatou",
  "session_date": "2026-08-27",
  "opened_at": "2026-08-27T08:00:00Z",
  "initial_cash": "25000.00",
  "expected_cash": "145000.00",
  "actual_cash_counted": null,
  "cash_difference": null,
  "status": "OPEN",
  "total_sales_count": 18
}
```

#### `POST /api/pharmacy/pos/session/open/`
- **Body JSON :**
```json
{
  "initial_cash": "25000.00",
  "notes": "Fond de caisse initial du matin"
}
```
- **Response JSON Succès (201 Created) :**
```json
{
  "id": 12,
  "cashier_username": "caissier_fatou",
  "session_date": "2026-08-27",
  "opened_at": "2026-08-27T08:00:00Z",
  "initial_cash": "25000.00",
  "expected_cash": "25000.00",
  "actual_cash_counted": null,
  "cash_difference": null,
  "status": "OPEN",
  "total_sales_count": 0
}
```
- **Response JSON Erreur si caisse déjà ouverte (400 Bad Request) :**
```json
{
  "code": "SESSION_ALREADY_OPEN",
  "error": "Une session de caisse est déjà ouverte pour ce caissier. Veuillez clôturer la session active avant d'en ouvrir une nouvelle.",
  "session": {
    "id": 12,
    "session_date": "2026-08-27",
    "initial_cash": "25000.00",
    "expected_cash": "145000.00",
    "status": "OPEN"
  }
}
```

#### `POST /api/pharmacy/pos/session/close/`
- **Body JSON :**
```json
{
  "actual_cash_counted": "145000.00",
  "notes": "Comptage validé avec le titulaire"
}
```
- **Response JSON (200 OK) :**
```json
{
  "id": 12,
  "cashier_username": "caissier_fatou",
  "session_date": "2026-08-27",
  "opened_at": "2026-08-27T08:00:00Z",
  "closed_at": "2026-08-27T18:00:00Z",
  "initial_cash": "25000.00",
  "expected_cash": "145000.00",
  "actual_cash_counted": "145000.00",
  "cash_difference": "0.00",
  "status": "CLOSED",
  "notes": "Comptage validé avec le titulaire",
  "total_sales_count": 18
}
```

#### `POST /api/pharmacy/pos/checkout/`

##### Option A : Paiement Simple (Ex: Espèces avec rendu de monnaie)
- **Body JSON :**
```json
{
  "items": [
    { "product_id": 1, "quantity": 2, "unit_price": "1500.00" }
  ],
  "payment_method": "ESPECE",
  "amount_received": "5000.00"
}
```

##### Option B : Paiement Mixte / Échelonné (Ex: 17 000 FCFA -> 10 000 Espèces + 7 000 Wave)
- **Body JSON :**
```json
{
  "items": [
    { "product_id": 12, "quantity": 1, "unit_price": "17000.00" }
  ],
  "payment_method": "MIXTE",
  "payments": [
    { "method": "ESPECE", "amount": "10000.00" },
    { "method": "WAVE", "amount": "7000.00" }
  ],
  "amount_received": "10000.00"
}
```
*(Remarque : Dans ce cas, le fond de caisse n'est incrémenté que des 10 000 FCFA d'espèces. Le reste est tracé en Wave).*

- **Response JSON Erreur si caisse non ouverte (400 Bad Request) :**
```json
{
  "code": "CASH_SESSION_REQUIRED",
  "error": "Aucune session de caisse ouverte pour ce caissier. Veuillez ouvrir la caisse avant d'effectuer un encaissement."
}
```

- **Response JSON Succès (201 Created) :**
```json
{
  "id": 1,
  "ticket_number": "VTE-20260828-4821",
  "cashier_username": "caissier_fatou",
  "customer": null,
  "customer_name": null,
  "total_ht": "17000.00",
  "total_tva": "0.00",
  "total_ttc": "17000.00",
  "payment_method": "MIXTE",
  "payment_method_display": "Paiement Mixte",
  "payment_details": [
    { "method": "ESPECE", "amount": "10000.00" },
    { "method": "WAVE", "amount": "7000.00" }
  ],
  "amount_received": "10000.00",
  "change_returned": "0.00",
  "status": "PAID",
  "items": [
    {
      "id": 1,
      "product": 12,
      "product_name": "Tensiomètre Électronique",
      "product_barcode": "3400939999999",
      "batch_number": "LOT-202610-0010",
      "expiration_date": "2027-10-31",
      "quantity": 1,
      "unit_price": "17000.00",
      "total_price": "17000.00"
    }
  ],
  "created_at": "2026-08-28T15:30:00Z"
}
```

#### `GET /api/pharmacy/pos/sales/` (Historique des Ventes & Facturation)
- **Query Params supportés :**
  - `?cashier_username=caissier_fatou` *(Filtre par caissier)*
  - `?date=2026-08-27` *(Filtre par date)*
  - `?payment_method=ESPECE|WAVE|OMONEY|COMPTE_CLIENT` *(Filtre par mode)*
  - `?search=VTE-2026` *(Recherche par ticket ou client)*
  - `?ordering=-created_at` *(Tri antéchronologique)*
- **Response JSON (200 OK) :**
```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "ticket_number": "VTE-20260827-4821",
      "cash_session": 12,
      "cashier": 3,
      "cashier_username": "caissier_fatou",
      "customer": null,
      "customer_name": null,
      "total_ht": "3000.00",
      "total_tva": "0.00",
      "total_ttc": "3000.00",
      "payment_method": "ESPECE",
      "payment_method_display": "Espèces",
      "amount_received": "5000.00",
      "change_returned": "2000.00",
      "status": "PAID",
      "status_display": "Payé",
      "items": [
        {
          "id": 1,
          "product": 1,
          "product_name": "Doliprane 1000mg Comprimés",
          "product_barcode": "3400930000010",
          "batch_number": "LOT-202610-0010",
          "expiration_date": "2026-10-31",
          "quantity": 2,
          "unit_price": "1500.00",
          "total_price": "3000.00"
        }
      ],
      "created_at": "2026-08-27T12:30:00Z"
    }
  ]
}
```

#### `GET /api/pharmacy/pos/sales/{id}/` (Détail Ticket & Impression / Facture)
- **Response JSON (200 OK) :** Renvoie l'objet vente complet avec ses lignes pour ré-impression thermique ou génération de facture PDF.

---

### 7. Comptes Clients & Ventes à Crédit

#### `GET /api/pharmacy/customers/accounts/`
- **Response JSON (200 OK) :**
```json
[
  {
    "id": 1,
    "name": "Mamadou Ndiaye",
    "phone": "771234567",
    "account_type": "PREPAID",
    "current_balance": "10000.00",
    "credit_limit": "5000.00",
    "available_credit": "15000.00",
    "is_active": true
  }
]
```

#### `POST /api/pharmacy/customers/accounts/`
- **Body JSON :**
```json
{
  "name": "Mamadou Ndiaye",
  "phone": "771234567",
  "account_type": "PREPAID",
  "credit_limit": "5000.00"
}
```

#### `POST /api/pharmacy/customers/accounts/{id}/deposit/`
- **Body JSON :**
```json
{
  "amount": "25000.00",
  "payment_method": "WAVE",
  "note": "Recharge acompte mensuel"
}
```

#### `GET /api/pharmacy/customers/accounts/{id}/statement/?month=2026-08`
- **Response JSON (200 OK) :**
```json
{
  "customer_id": 1,
  "customer_name": "Mamadou Ndiaye",
  "phone": "771234567",
  "account_type": "PREPAID",
  "current_balance": "35000.00",
  "credit_limit": "5000.00",
  "total_deposits_period": "25000.00",
  "total_purchases_period": "0.00",
  "transactions": []
}
```

---

### 8. Fournisseurs, Commandes & Réclamations

#### `GET /api/pharmacy/suppliers/`
- **Response JSON (200 OK) :**
```json
[
  {
    "id": 1,
    "name": "Laborex Sénégal",
    "phone": "338390000",
    "address": "Route de Rufisque, Dakar",
    "contact_person": "M. Diallo",
    "order_website_url": "https://portail.laborex.sn",
    "is_active": true
  }
]
```

#### `POST /api/pharmacy/suppliers/`
- **Body JSON :**
```json
{
  "name": "Laborex Sénégal",
  "phone": "338390000",
  "address": "Route de Rufisque, Dakar",
  "contact_person": "M. Diallo",
  "order_website_url": "https://portail.laborex.sn"
}
```

#### `POST /api/pharmacy/suppliers/orders/generate-from-sales/?period=today|week`
- **Body JSON :**
```json
{
  "supplier_id": 1
}
```
- **Response JSON (201 Created) :**
```json
{
  "id": 1,
  "supplier": 1,
  "supplier_name": "Laborex Sénégal",
  "order_number": "CMD-20260826-8910",
  "status": "DRAFT",
  "status_display": "Brouillon / Proposition",
  "total_amount_ht": "45000.00",
  "items": [
    {
      "id": 1,
      "product": 1,
      "product_name": "Doliprane 1000mg Comprimés",
      "product_barcode": "3400930000010",
      "quantity_ordered": 30,
      "quantity_received": 0,
      "unit_purchase_price": "1000.00"
    }
  ]
}
```

#### `POST /api/pharmacy/suppliers/orders/{id}/import-delivery-csv/`
- **Request Form-Data :** `file: bon_livraison.csv`
- **Response JSON (200 OK) :**
```json
{
  "status": "success",
  "message": "Bon de livraison réceptionné avec succès et stock mis à jour.",
  "total_quantity_received": 30,
  "batches_processed": 1,
  "order_status": "RECEIVED"
}
```

#### `POST /api/pharmacy/suppliers/claims/`
- **Request Form-Data / JSON :**
```json
{
  "supplier": 1,
  "claim_type": "DAMAGED",
  "product_name": "Doliprane 1000mg",
  "batch_number": "LOT-202610-0010",
  "quantity_affected": 2,
  "description": "Boîtes écrasées lors du déchargement"
}
```

---

### 9. Dépenses d'Exploitation & États Financiers Consolidés

#### `POST /api/pharmacy/billing/expenses/`
- **Body JSON (Création simple et rapide) :**
```json
{
  "category": 1,
  "amount": "15000.00",
  "payment_method": "ESPECE",
  "date": "2026-08-26",
  "description": ""
}
```
*(Remarque : `description` et `receipt_file` sont facultatifs).*
- **Response JSON (201 Created) :**
```json
{
  "id": 1,
  "category": 1,
  "category_name": "Loyer Officine",
  "amount": "15000.00",
  "payment_method": "ESPECE",
  "payment_method_display": "Espèces",
  "description": "",
  "receipt_file": null,
  "date": "2026-08-26",
  "created_by": 2,
  "created_by_username": "pharmacien_ali",
  "created_at": "2026-08-26T14:00:00Z",
  "updated_at": "2026-08-26T14:00:00Z"
}
```

#### `GET /api/pharmacy/financial-statement/?period=today|week|month|custom&start_date=2026-08-01&end_date=2026-08-31`
- **Response JSON (200 OK) :**
```json
{
  "period": "month",
  "start_date": "2026-08-01",
  "end_date": "2026-08-31",
  "pharmacy_name": "Grande Pharmacie Dakar",
  "pharmacy_id": "MT4829104K",
  "total_ventes_ttc": "4850000.00",
  "total_ventes_ht": "4850000.00",
  "total_tva_collectee": "0.00",
  "total_depenses": "850000.00",
  "solde_net": "4000000.00",
  "cout_achat_marchandises": "3200000.00",
  "marge_brute_estimee": "1650000.00",
  "taux_marge_pourcentage": 34.02,
  "total_tickets_count": 1240,
  "panier_moyen": "3911.29",
  "ventilation_modes_paiement": {
    "ESPECE": { "label": "Espèces", "total": "2900000.00", "percentage": 59.79 },
    "WAVE": { "label": "Wave", "total": "1450000.00", "percentage": 29.90 },
    "OMONEY": { "label": "Orange Money", "total": "500000.00", "percentage": 10.31 }
  },
  "ventilation_categories_depenses": [
    { "category": "Loyer Officine", "total": "500000.00" },
    { "category": "Électricité / Senelec", "total": "250000.00" }
  ],
  "creances_clients_total": "125000.00",
  "acomptes_clients_total": "450000.00"
}
```

---

# PARTIE 3 : PROMPT D'INGÉNIERIE CLÉ EN MAIN POUR LE WORKSPACE FRONTEND

*(Copiez-collez l'intégralité du texte ci-dessous dans la discussion de votre nouveau workspace Frontend)*

```markdown
# PROMPT D'INGÉNIERIE FRONTEND : SAAS PHARMACIE & CAISSE POS (REACT + TYPESCRIPT)

Nous construisons l'application Web Frontend de notre **SaaS de Gestion d'Officine de Pharmacie et Point de Vente (POS)** 100% en Français, connecté à l'API Django 6.0+ avec PostgreSQL Row-Level Security (RLS).

---

## 1. STACK TECHNIQUE & RECOMMANDATIONS STRICTES
- **Framework :** React (Vite) + TypeScript + React Compiler + ESLint.
- **Styling :** Tailwind CSS + Lucide React.
- **State Management & Fetching :** TanStack Query (React Query v5) + Zustand pour le panier de caisse.
- **Formulaires :** React Hook Form + Zod.
- **Format & Date :** date-fns (locale `fr`), Intl.NumberFormat (FCFA).
- **Zéro Hardcoding :** 100% Component-Driven. Tous les boutons, champs, modaux, cartes et badges doivent provenir de `/src/components/ui/`.
- **Zéro Suppression :** Sur toutes les routes de l'officine (stocks, ventes, clients, fournisseurs), le bouton Supprimer est formellement interdit (conformité comptable).
- **Suivi des Tâches :** Tu dois créer et maintenir un fichier `TODO.md` à la racine pour cocher chaque étape réalisée.

---

## 2. SPÉCIFICATIONS FONCTIONNELLES CRITIQUES

### A. Authentification & URL Bookmarkable
- URL de connexion : supporte `http://localhost:5174/login?tenant=MTXXXXXXXL`.
- Si le paramètre `tenant` est présent dans l'URL, il est mémorisé dans un stockage local dédié `pharma_login_tenant_id` pour faciliter la reconnexion.
- **Sécurité :** L'authentification réelle auprès de l'API repose exclusivement sur les claims du JWT décodé (`tenant_id`, `role`, `pharmacy_name`, `subscription_status`).
- Deux espaces étanches :
  1. **Propriétaire SaaS (`role === 'SAAS_OWNER'`) :** Redirigé vers `/saas/dashboard`. Accès aux officines, abonnements et au catalogue national partagé.
  2. **Personnel de l'Officine (`ADMIN`, `PHARMACIEN`, `CAISSIER`, `COMPTABLE`) :** Redirigé vers `/pos` ou `/dashboard`. Aucune visibilité sur l'espace SaaS Admin.

### B. Gestion des Utilisateurs par le Titulaire (3 Options Claires)
Dans la vue Équipe (`/settings/team`), lors de la création d'un utilisateur, le titulaire dispose d'un sélecteur à 3 options :
1. *Générer un mot de passe automatique* : Le mot de passe généré s'affiche immédiatement dans une alerte avec bouton "Copier".
2. *Saisir sur place avec l'employé* : Champ de saisie classique du mot de passe avec confirmation.
3. *Générer et envoyer par email* : Génération automatique et envoi des identifiants via l'API.

### C. Caisse POS, Scan Hybride & Top 10 Produits Phares
- **Top 10 Produits Phares (Quick-Add) :**
  - À côté de la barre de recherche et du panier, un panneau de cartes d'accès rapide affiche les **10 produits les plus vendus** (`GET /api/pharmacy/pos/top-products/`).
  - Un simple clic sur une carte ajoute instantanément 1 unité au panier.
- **Contrôle Strict de Caisse :**
  - Au chargement du POS, vérifier `GET /api/pharmacy/pos/session/current/`. Si `has_open_session === false`, afficher la modale bloquante "Ouverture de Caisse" (saisie du fond de caisse initial) et désactiver l'encaissement.
- **Desktop (Douchette USB) :** Listener global sur les frappes rapides de code-barres (EAN-13/CIP) permettant d'ajouter instantanément le produit au panier sans focus préalable.
- **Mobile (Caméra Barcode Scanner) :**
  - Modal caméra avec détection automatique (via `html5-qrcode` ou `@zxing/library`).
  - La permission caméra doit être demandée une seule fois et conservée de manière persistante.
  - Dès qu'un code-barres est détecté, la caméra **se ferme immédiatement** et l'article est ajouté au panier (éviter toute boucle de scan infinie).
- **Encaissement & Rendu de Monnaie :**
  - Si paiement `ESPECE` : Le caissier saisit le montant remis. Le frontend calcule en temps réel `Monnaie Rendue = Montant Reçu - Total TTC`. Le ticket thermique s'affiche avec la monnaie rendue.
  - Si paiement `WAVE` ou `OMONEY` : Aucun calcul de rendu de monnaie n'est affiché (montant exact).
  - Si paiement `COMPTE_CLIENT` : Affiche le solde actuel du client et vérifie immédiatement si le plafond de crédit autorisé est suffisant.
- **Impression Ticket Thermique :** Composant prêt pour impression thermique 80mm/58mm via CSS `@media print`.

### D. Stocks, Péremptions & Commande Express
- **Alertes Péremption en Rouge :** Tout produit dont le lot le plus proche expire dans moins de 3 mois (`is_expiring_soon === true`) doit être affiché avec un badge rouge vif et date surlignée en rouge.
- **Stat Cards du Stock :** Affichent : Valeur totale du stock, Nombre de références, Nombre de produits en rupture (`is_low_stock`), et **Nombre de produits proches de la péremption (< 3 mois)**.
- **Commande Express depuis le Stock :** Bouton rapide filtrant les produits ayant `quantite < 2` (ou sous leur seuil d'alerte), avec bouton d'export CSV immédiat prêt pour le portail du grossiste.

### E. Factures Officielles (Invoice PDF)
- Bouton "Générer Facture PDF" présent sur les détails d'une vente ou d'un compte client.
- La facture n'est générée **que sur demande explicite de l'utilisateur**.
- Contient l'en-tête officiel de l'officine (Logo, Nom, Agrément, Téléphone, Adresse), les coordonnées client, le tableau détaillé des articles (Désignation, Qté, Prix Unitaire, Total) et le récapitulatif financier.

---

## 3. INSTRUCTIONS DE DÉMARRAGE IMMÉDIAT
1. Initialise le fichier `TODO.md` avec toutes les étapes.
2. Met en place les types TypeScript stricts dans `/src/types/`.
3. Configure Axios / Fetch avec injecteur de token JWT et gestion automatique des erreurs 401 et 403 (`SUBSCRIPTION_REQUIRED`).
4. Développe le Design System dans `/src/components/ui/`.
5. Implémente les flux POS, Stocks, Commandes, Dépenses et SaaS Admin.
```
