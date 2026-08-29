# Suivi des Tâches Backend & POS (TODO.md)

- [x] 1. Création de `TODO.md` pour le suivi des modifications
- [x] 2. Implémentation du endpoint `GET /api/pharmacy/pos/top-products/` (Top 10 des produits phares)
- [x] 3. Verrouillage strict de l'ouverture de caisse : Rejet avec `SESSION_ALREADY_OPEN` si une session est déjà `OPEN`
- [x] 4. Verrouillage strict des ventes : Rejet de `POST /api/pharmacy/pos/checkout/` avec `CASH_SESSION_REQUIRED` si aucune caisse n'est ouverte
- [x] 5. Filtrage des ventes par `cashier_username`, `date`, et `payment_method` sur `GET /api/pharmacy/pos/sales/`
- [x] 6. Ajout des tests automatisés dans `tests/test_pos_checkout.py`
- [x] 7. Validation complète de la suite de tests (29/29 tests validés avec succès)
- [x] 8. Mise à jour de `FRONTEND_ARCHITECTURE_AND_PROMPT.md` avec les contrats d'interface JSON détaillés
- [x] 9. Mise à jour du modèle `MedicamentCatalog` (`alternate_barcode`, `geo_code`, catégorie optionnelle)
- [x] 10. Création et application des migrations Django pour `catalog` (catalog.0002)
- [x] 11. Mise à jour de `MedicamentCatalogSerializer` et `MedicamentCatalogViewSet`
- [x] 12. Création de la commande de gestion `populate_national_catalog`
- [x] 13. Exécution de l'importation des 3 991 références depuis `export-stocks-26_08_2026 00_34.csv`
- [x] 14. Ajout et exécution des tests automatisés pour le catalogue (32/32 tests OK)
- [x] 15. Mise à jour de `FRONTEND_ARCHITECTURE_AND_PROMPT.md` avec les nouveaux champs du catalogue
- [x] 16. Optimisation complète du `Dockerfile` (suppression des paquets inutiles de compilation/WeasyPrint, passage en Debian slim léger, utilisateur non-root)
- [x] 17. Configuration CORS, CSRF et en-têtes proxy HTTPS pour `https://pharmacy.melakhtelecom.com` dans `core/settings/production.py`
- [x] 18. Désactivation conditionnelle de Swagger / ReDoc en production (`ENABLE_SWAGGER=False`)
- [x] 19. Création du endpoint de healthcheck `/api/health/` et intégration dans `entrypoint.sh` avec `core.wsgi:application`
- [x] 20. Création des fichiers `.env.production`, `.env.example` et `docker-stack.yml` pour le déploiement Docker Swarm
- [x] 21. Optimisation CPU Django : Mise en cache Redis (`pos_top_products:{id}`, `sub_valid:{id}`) avec invalidation atomique
- [x] 22. Élimination du churn de connexions TCP/DB avec `CONN_MAX_AGE=60` et `CONN_HEALTH_CHECKS=True`
- [x] 23. Configuration fine de Gunicorn (`3 workers x 4 threads`, recyclage `max-requests=2000`, `--worker-tmp-dir /dev/shm`)
- [x] 24. Tuning PostgreSQL pour VPS Contabo 8GB RAM (`shared_buffers=2GB`, `effective_cache_size=6GB`, `work_mem=32MB`)
- [x] 25. Pipeline CI/CD GitHub Actions complet avec Quality Gates (Lint, Sécurité, Tests PostgreSQL+Redis, Build Docker, Déploiement Swarm)
- [x] 26. Prise en charge des Paiements Mixtes / Échelonnés (ex: 17 000 FCFA -> ESPECE: 10 000 + WAVE: 7 000) avec incrémentation sélective du fond de caisse et validation multi-modes (37/37 tests OK)




