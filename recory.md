Thought for 14s
Crafting Comprehensive Architectures
☁️ Stratégie Hybride de Continuité d'Activité & Disaster Recovery (DR)
Rôle : Senior Cloud Solutions Architect & DevOps Engineer
Objectif : Disponibilité Maximale (99.9% +) sans surcoût AWS permanent (<$3/mois en veille).
Environnement Principal : VPS Contabo 4 vCPU / 8 Go RAM (https://pharmacy.melakhtelecom.com)
Environnement de Secours (Failover) : AWS Cloud Native (S3, Route 53, App Runner / EC2 On-Demand)
──────

## 1. Architecture Globale : Modèle Pilot Light / Serverless On-Demand

Pour une startup ou PME, faire tourner des instances EC2/RDS Multi-AZ 24h/24 sur AWS génère un coût de $150 à $300/mois.
Le modèle Pilot Light Hybride permet de bénéficier de la haute disponibilité d'AWS tout en maintenant le coût en veille à moins de $3/mois :

                                      UTILISATEURS / PHARMACIES
                                                  │
                                                  ▼
                                 ┌──────────────────────────────────┐
                                 │    Amazon Route 53 DNS Failover  │
                                 │  (Sonde /api/health/ toutes les 15s)
                                 └────────────────┬─────────────────┘
                                                  │
                         ┌────────────────────────┴────────────────────────┐
              (NORMAL - PRIMAIRE)                                (PANNE - SECONDAIRE)
                         │                                                 │
                         ▼                                                 ▼
            ┌─────────────────────────┐                       ┌─────────────────────────┐
            │      CONTABO VPS        │                       │       AWS DR TARGET     │
            │  • Gunicorn (2 réplicas)│                       │  • AWS App Runner / EC2 │
            │  • PostgreSQL 16 (RLS)  │                       │  • PostgreSQL On-Demand │
            │  • Redis Cache          │                       │  • Coût actif seulement │
            │  • Traefik Proxy        │                       │    durant l'incident    │
            └────────────┬────────────┘                       └────────────▲────────────┘
                         │                                                 │
                         │  1. Dump Chiffré AES-256 (Toutes les heures)    │
                         │  2. Sync des Médias / Ordonnances               │
                         └────────────────────────┬────────────────────────┘
                                                  │
                                                  ▼
                                 ┌──────────────────────────────────┐
                                 │       Amazon S3 Backup Vault     │
                                 │   (Chiffrement SSE-S3 + Versioning│
                                 │   Lifecycle: IA -> Glacier Inst.) │
                                 │        Coût : ~0.30$/mois        │
                                 └──────────────────────────────────┘

──────

## 2. Métriques de Résilience : RPO & RTO

| Métrique                               | Valeur Cible    | Description                                                                                  |
| -------------------------------------- | --------------- | -------------------------------------------------------------------------------------------- |
| RPO (Recovery Point Objective)         | ≤ 30 minutes    | Perte maximale théorique de données limitée au dernier delta horaire synchronisé sur S3.     |
| RTO (Recovery Time Objective)          | ≤ 3 à 5 minutes | Temps nécessaire pour basculer le trafic DNS et démarrer le secours AWS à partir du dump S3. |
| Coût AWS en Mode Normal (99% du temps) | ≈ $2.50 / mois  | Uniquement le stockage S3 et la zone DNS Route 53.                                           |

──────

## 3. Pilier 1 : Pipeline de Sauvegarde Automatisée (backup_to_s3.sh)

Le script a été créé et intégré dans le dépôt. Il garantit :

1. Chiffrement Côté Client (Zero Secret Leakage) : Le dump PostgreSQL binaire est compressé puis chiffré en AES-256-CBC avec PBKDF2 (100 000 itérations) avant de
   quitter le VPS. Même si le bucket S3 était compromis, les données restent indéchiffrables.
2. Synchronisation des Médias : Synchronisation incrémentale du volume /app/media (justificatifs de caisse, ordonnances).
3. Pointeur Rapide : Met à jour automatiquement latest.dump.enc sur S3 pour une restauration instantanée en 1 commande.

### Déploiement du Cron de Sauvegarde sur Contabo

Exécutez sur votre VPS :

    # Ouvrir la crontab
    crontab -e

    # Sauvegarde automatique toutes les heures (à la minute 15)
    15 * * * * /bin/bash /opt/pharmaback/scripts/backup_to_s3.sh >> /var/log/pharmaback_backup.log 2>&1

──────

## 4. Pilier 2 : Sécurité IAM à Moindre Privilège (Least Privilege)

Créez un utilisateur IAM dédié nommé pharmaback-contabo-agent avec exclusivement la politique suivante (aucun accès console, aucun droit EC2/RDS) :

    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Sid": "AllowS3BackupAndRestoreOperations",
          "Effect": "Allow",
          "Action": [
            "s3:PutObject",
            "s3:GetObject",
            "s3:ListBucket",
            "s3:DeleteObject"
          ],
          "Resource": [
            "arn:aws:s3:::pharmaback-disaster-recovery-backups",
            "arn:aws:s3:::pharmaback-disaster-recovery-backups/*"
          ]
        }
      ]
    }

### Cycle de Vie S3 (S3 Lifecycle Policy) pour Réduire les Coûts

Dans la console Amazon S3 > Management > Lifecycle Rules :

• Transition à 14 jours : Déplacer vers S3 Standard-Infrequent Access (IA).
• Transition à 30 jours : Déplacer vers Glacier Instant Retrieval.
• Expiration à 90 jours : Suppression automatique des anciennes archives.
──────

## 5. Pilier 3 : Surveillance Active & Bascule DNS (Amazon Route 53)

Configurez le routage de basculement (DNS Failover Routing) dans Route 53 :

                                  Route 53 Health Check
                           Probe: https://api.pharmacy.melakhtelecom.com/api/health/
                           Interval: 10 secondes | Seuil d'échec : 3 (30s)
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       │                                           │
             [Si Statut = HEALTHY]                       [Si Statut = UNHEALTHY]
                       │                                           │
                       ▼                                           ▼
          Enregistrement PRIMARY (A)                  Enregistrement SECONDARY (A / CNAME)
            IP du VPS Contabo                           URL / IP de secours AWS

• Notification Instantanée : Connectez l'alarme CloudWatch associée au Health Check à un sujet Amazon SNS (Email, SMS, ou webhook Discord/Telegram/Slack) pour être
alerté en direct dès le début d'un incident.
──────

## 6. Pilier 4 : Procédure de Déclenchement du Secours (restore_from_s3.sh)

Si Contabo est indisponible (ex: panne réseau majeure) :

### Option A : Déclenchement Manuel Rapide (Moins de 3 minutes)

1. Démarrer une instance EC2 t4g.small (ARM64 - $0.0168/heure) ou un conteneur AWS App Runner pré-configuré.
2. Lancer la restauration automatique :
   export AWS_S3_BACKUP_BUCKET="pharmaback-disaster-recovery-backups"
   export BACKUP_ENCRYPTION_PASSPHRASE="VotreCleSecreteDeChiffrement"

   # Restaure automatiquement la dernière version de la base et des fichiers médias

   ./scripts/restore_from_s3.sh latest.dump.enc

3. L'API est instantanément opérationnelle sur AWS.

### Option B : Déclenchement Automatique via GitHub Actions

Un workflow disaster-recovery.yml déclenchable via un simple bouton (workflow_dispatch) ou par webhook AWS Lambda peut instancier la stack sur AWS sans aucune
intervention manuelle.
──────

## 7. Procédure de Rétablissement (Failback vers Contabo)

Lorsque Contabo revient en ligne après maintenance :

1. Exécuter un backup sur l'instance AWS de secours vers S3.
2. Exécuter ./scripts/restore_from_s3.sh sur le VPS Contabo.
3. Route 53 détecte automatiquement le retour à l'état HEALTHY de Contabo et réoriente le trafic vers le VPS principal en toute transparence.
4. Éteindre l'instance AWS pour stopper toute facturation.
