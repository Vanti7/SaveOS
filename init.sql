-- Script d'initialisation de la base de données SaveOS
-- Ce script sera exécuté automatiquement par PostgreSQL au démarrage

-- Créer la base de données si elle n'existe pas (déjà fait par POSTGRES_DB)
-- Mais on peut ajouter des configurations spécifiques ici

-- Extensions utiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Index pour améliorer les performances
-- (Les tables seront créées par SQLAlchemy)

-- Configuration PostgreSQL pour de meilleures performances
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET log_statement = 'all';
ALTER SYSTEM SET log_min_duration_statement = 1000;

-- Recharger la configuration
SELECT pg_reload_conf();