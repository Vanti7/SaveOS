#!/usr/bin/env python3
"""
Agent CLI SaveOS - Interface en ligne de commande pour l'agent de sauvegarde
"""
import click
import json
import os
import tempfile
import time
import sys
import threading
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from agent.config import AgentConfig
from agent.api_client import SaveOSAPIClient
from agent.service import ServiceManager

@click.group()
@click.option('--config-dir', help='Répertoire de configuration personnalisé')
@click.pass_context
def cli(ctx, config_dir):
    """Agent CLI SaveOS - Système de sauvegarde centralisé"""
    ctx.ensure_object(dict)
    ctx.obj['config'] = AgentConfig(config_dir)

@cli.command()
@click.option('--api-url', help='URL de l\'API SaveOS')
@click.option('--verify-ssl/--no-verify-ssl', default=None,
              help='Force la vérification du certificat TLS (par défaut : '
                   'auto-détecté selon l\'hôte, désactivé seulement pour localhost/127.0.0.1)')
@click.option('--registration-secret', default=None,
              help="Secret d'enregistrement du tenant (affiché une seule fois à la création du tenant)")
@click.pass_context
def register(ctx, api_url, verify_ssl, registration_secret):
    """Enregistre l'agent auprès du serveur SaveOS"""
    config_manager = ctx.obj['config']
    config = config_manager.load_config()

    if api_url:
        config['api_url'] = api_url
        if verify_ssl is None:
            config['verify_ssl'] = AgentConfig._default_verify_ssl(api_url)
        config_manager.save_config(config)
    if verify_ssl is not None:
        config['verify_ssl'] = verify_ssl
        config_manager.save_config(config)
    if registration_secret:
        config['registration_secret'] = registration_secret
        config_manager.save_config(config)

    if not config.get('registration_secret'):
        click.echo("❌ Secret d'enregistrement manquant. Utilisez --registration-secret "
                    "(fourni à la création du tenant, voir 'tenant create' côté serveur).", err=True)
        sys.exit(1)

    click.echo(f"🔗 Enregistrement auprès de {config['api_url']}...")

    # Créer le client API
    client = SaveOSAPIClient(config['api_url'], verify_ssl=config['verify_ssl'])

    # Enregistrer l'agent
    result = client.register_agent(
        hostname=config['hostname'],
        platform=config['platform'],
        registration_secret=config['registration_secret'],
        config={
            'source_paths': config['source_paths'],
            'repo_path': config['repo_path'],
            'passphrase': config['passphrase']
        }
    )
    
    if result['success']:
        agent_data = result['data']
        token = agent_data['token']
        
        # Sauvegarder le token
        if config_manager.save_token(token):
            click.echo(f"✅ Agent enregistré avec succès!")
            click.echo(f"   ID: {agent_data['id']}")
            click.echo(f"   Hostname: {agent_data['hostname']}")
            click.echo(f"   Platform: {agent_data['platform']}")
            click.echo(f"   Status: {agent_data['status']}")
            click.echo(f"   Token sauvegardé dans: {config_manager.token_file}")
        else:
            click.echo("❌ Erreur lors de la sauvegarde du token", err=True)
            sys.exit(1)
    else:
        click.echo(f"❌ Erreur lors de l'enregistrement: {result['error']}", err=True)
        sys.exit(1)

@cli.command()
@click.option('--token', required=True, help="Token d'un agent déjà provisionné depuis le tableau de bord")
@click.pass_context
def configure(ctx, token):
    """Configure l'agent avec un token déjà provisionné (tableau de bord ->
    Téléchargements) — aucun appel réseau, contrairement à register qui
    exige un secret d'enregistrement de tenant."""
    config_manager = ctx.obj['config']

    if config_manager.save_token(token):
        click.echo("✅ Agent configuré avec le token fourni.")
        click.echo(f"   Token sauvegardé dans: {config_manager.token_file}")
    else:
        click.echo("❌ Erreur lors de la sauvegarde du token", err=True)
        sys.exit(1)

@cli.command()
@click.pass_context
def status(ctx):
    """Affiche le statut de l'agent et les statistiques"""
    config_manager = ctx.obj['config']
    config = config_manager.load_config()
    token = config_manager.get_token()
    
    if not token:
        click.echo("❌ Agent non enregistré. Utilisez 'register' d'abord.", err=True)
        sys.exit(1)
    
    client = SaveOSAPIClient(config['api_url'], token, config['verify_ssl'])
    
    # Vérifier la santé de l'API
    health_result = client.health_check()
    if not health_result['success']:
        click.echo(f"❌ API non accessible: {health_result['error']}", err=True)
        sys.exit(1)
    
    # Récupérer les statistiques
    stats_result = client.get_agent_stats()
    if stats_result['success']:
        stats = stats_result['data']
        click.echo("📊 Statut de l'agent:")
        click.echo(f"   Status: {stats['status']}")
        click.echo(f"   Total snapshots: {stats['total_snapshots']}")
        click.echo(f"   Taille totale: {_format_bytes(stats['total_size_bytes'])}")
        if stats['last_backup']:
            last_backup = datetime.fromisoformat(stats['last_backup'].replace('Z', '+00:00'))
            click.echo(f"   Dernière sauvegarde: {last_backup.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            click.echo("   Dernière sauvegarde: Aucune")
    else:
        click.echo(f"❌ Erreur lors de la récupération des stats: {stats_result['error']}", err=True)

@cli.command()
@click.option('--source-paths', help='Chemins à sauvegarder (séparés par des virgules)')
@click.option('--wait', is_flag=True, help='Attendre la fin du job')
@click.pass_context
def backup(ctx, source_paths, wait):
    """Lance une sauvegarde"""
    config_manager = ctx.obj['config']
    config = config_manager.load_config()
    token = config_manager.get_token()
    
    if not token:
        click.echo("❌ Agent non enregistré. Utilisez 'register' d'abord.", err=True)
        sys.exit(1)
    
    # Récupérer l'ID de l'agent depuis le token (pour simplifier, on fait un heartbeat)
    client = SaveOSAPIClient(config['api_url'], token, config['verify_ssl'])
    
    # Envoyer un heartbeat pour récupérer l'ID de l'agent
    heartbeat_result = client.send_heartbeat()
    if not heartbeat_result['success']:
        click.echo(f"❌ Erreur lors du heartbeat: {heartbeat_result['error']}", err=True)
        sys.exit(1)
    
    # Pour simplifier, on assume que l'agent_id est 1 (dans un vrai système, il faudrait le récupérer)
    agent_id = 1  # TODO: Récupérer l'ID réel de l'agent
    
    # Préparer la configuration du job
    job_config = {
        'source_paths': source_paths.split(',') if source_paths else config['source_paths'],
        'repo_path': config['repo_path'],
        'passphrase': config['passphrase']
    }
    
    click.echo("🚀 Lancement de la sauvegarde...")
    click.echo(f"   Chemins: {', '.join(job_config['source_paths'])}")
    
    # Créer le job de sauvegarde
    job_result = client.create_backup_job(agent_id, job_config)
    
    if job_result['success']:
        job_data = job_result['data']
        job_id = job_data['id']
        click.echo(f"✅ Job de sauvegarde créé (ID: {job_id})")
        
        if wait:
            click.echo("⏳ Attente de la fin du job...")
            _wait_for_job_completion(client, job_id)
    else:
        click.echo(f"❌ Erreur lors de la création du job: {job_result['error']}", err=True)
        sys.exit(1)

@cli.command()
@click.pass_context
def snapshots(ctx):
    """Liste les snapshots disponibles"""
    config_manager = ctx.obj['config']
    config = config_manager.load_config()
    token = config_manager.get_token()
    
    if not token:
        click.echo("❌ Agent non enregistré. Utilisez 'register' d'abord.", err=True)
        sys.exit(1)
    
    client = SaveOSAPIClient(config['api_url'], token, config['verify_ssl'])
    
    # Pour simplifier, on assume que l'agent_id est 1
    agent_id = 1  # TODO: Récupérer l'ID réel de l'agent
    
    snapshots_result = client.list_snapshots(agent_id)
    
    if snapshots_result['success']:
        snapshots_list = snapshots_result['data']
        if snapshots_list:
            click.echo("📸 Snapshots disponibles:")
            for snapshot in snapshots_list:
                created_at = datetime.fromisoformat(snapshot['created_at'].replace('Z', '+00:00'))
                click.echo(f"   • {snapshot['name']}")
                click.echo(f"     Taille: {_format_bytes(snapshot['size_bytes'])}")
                click.echo(f"     Créé le: {created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                click.echo(f"     Type: {'Full' if snapshot['is_full'] else 'Incrémental'}")
                click.echo()
        else:
            click.echo("📭 Aucun snapshot trouvé")
    else:
        click.echo(f"❌ Erreur lors de la récupération des snapshots: {snapshots_result['error']}", err=True)

@cli.command()
@click.option('--interval', default=300, help='Intervalle en secondes entre les heartbeats')
@click.pass_context
def daemon(ctx, interval):
    """Lance l'agent en mode daemon avec heartbeats réguliers"""
    config_manager = ctx.obj['config']
    config = config_manager.load_config()
    token = config_manager.get_token()
    
    if not token:
        click.echo("❌ Agent non enregistré. Utilisez 'register' d'abord.", err=True)
        sys.exit(1)
    
    client = SaveOSAPIClient(config['api_url'], token, config['verify_ssl'])
    
    click.echo(f"🔄 Démarrage du daemon (heartbeat toutes les {interval}s)")
    click.echo("   Appuyez sur Ctrl+C pour arrêter")
    
    try:
        while True:
            heartbeat_result = client.send_heartbeat("active")
            if heartbeat_result['success']:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                click.echo(f"💓 Heartbeat envoyé à {timestamp}")
            else:
                click.echo(f"❌ Erreur heartbeat: {heartbeat_result['error']}", err=True)

            _apply_pending_restores(client)

            time.sleep(interval)
    except KeyboardInterrupt:
        click.echo("\n🛑 Arrêt du daemon")

@cli.command()
@click.pass_context
def config_show(ctx):
    """Affiche la configuration actuelle"""
    config_manager = ctx.obj['config']
    config = config_manager.load_config()
    
    click.echo("⚙️  Configuration actuelle:")
    click.echo(f"   Fichier: {config_manager.config_file}")
    click.echo(f"   API URL: {config['api_url']}")
    click.echo(f"   Hostname: {config['hostname']}")
    click.echo(f"   Platform: {config['platform']}")
    click.echo(f"   Chemins sources: {', '.join(config['source_paths'])}")
    click.echo(f"   Repository: {config['repo_path']}")
    click.echo(f"   Heartbeat: {config['heartbeat_interval']}s")
    click.echo(f"   Vérification SSL: {config['verify_ssl']}")
    
    token = config_manager.get_token()
    if token:
        click.echo(f"   Token: Configuré ({token[:8]}...)")
    else:
        click.echo("   Token: Non configuré")

def _current_agent_path() -> str:
    """Chemin de l'exécutable (figé) ou du script courant, pour ServiceManager."""
    if getattr(sys, 'frozen', False):
        return sys.executable
    return os.path.abspath(__file__)

@click.group()
def service():
    """Gère l'agent comme service système (installation, démarrage, arrêt, statut)"""

@service.command('install')
def service_install():
    """Installe l'agent comme service système à démarrage automatique"""
    result = ServiceManager(_current_agent_path()).install_service()
    if result['success']:
        click.echo(f"✅ {result.get('message', 'Service installé')}")
    else:
        click.echo(f"❌ {result['error']}", err=True)
        sys.exit(1)

@service.command('start')
def service_start():
    """Démarre le service"""
    result = ServiceManager(_current_agent_path()).start_service()
    if result['success']:
        click.echo(f"✅ {result.get('message', 'Service démarré')}")
    else:
        click.echo(f"❌ {result['error']}", err=True)
        sys.exit(1)

@service.command('stop')
def service_stop():
    """Arrête le service"""
    result = ServiceManager(_current_agent_path()).stop_service()
    if result['success']:
        click.echo(f"✅ {result.get('message', 'Service arrêté')}")
    else:
        click.echo(f"❌ {result['error']}", err=True)
        sys.exit(1)

@service.command('status')
def service_status():
    """Affiche le statut du service"""
    result = ServiceManager(_current_agent_path()).get_service_status()
    if result['success']:
        click.echo(f"Status: {result['status']}")
    else:
        click.echo(f"❌ {result['error']}", err=True)
        sys.exit(1)

cli.add_command(service)

@cli.command()
@click.pass_context
def apply_restores(ctx):
    """Récupère et applique les restaurations en attente pour cet agent"""
    config_manager = ctx.obj['config']
    config = config_manager.load_config()
    token = config_manager.get_token()

    if not token:
        click.echo("❌ Agent non enregistré. Utilisez 'register' d'abord.", err=True)
        sys.exit(1)

    client = SaveOSAPIClient(config['api_url'], token, config['verify_ssl'])
    _apply_pending_restores(client)

def _apply_pending_restores(client: SaveOSAPIClient) -> None:
    """Récupère les restaurations en attente (status=ready_for_agent) et les
    applique localement : télécharge le paquet zip déjà extrait par le
    worker et le décompresse vers restore_path."""

    pending_result = client.list_pending_restores()
    if not pending_result['success']:
        click.echo(f"❌ Erreur lors de la récupération des restaurations en attente: {pending_result['error']}", err=True)
        return

    for pending in pending_result['data']:
        job_id = pending['id']
        restore_path = (pending.get('config') or {}).get('restore_path')

        if not restore_path:
            client.report_job_status(job_id, 'failed', "restore_path manquant dans la configuration du job")
            continue

        click.echo(f"📥 Restauration en attente (job {job_id}) -> {restore_path}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = str(Path(tmp_dir) / f"restore_{job_id}.zip")
            download_result = client.download_restore_package(job_id, zip_path)

            if not download_result['success']:
                click.echo(f"❌ Échec du téléchargement du paquet: {download_result['error']}", err=True)
                client.report_job_status(job_id, 'failed', download_result['error'])
                continue

            try:
                os.makedirs(restore_path, exist_ok=True)
                with zipfile.ZipFile(zip_path) as zf:
                    zf.extractall(restore_path)
            except Exception as e:
                click.echo(f"❌ Échec de l'extraction: {e}", err=True)
                client.report_job_status(job_id, 'failed', str(e))
                continue

        client.report_job_status(job_id, 'completed')
        click.echo(f"✅ Restauration appliquée (job {job_id})")

def _format_bytes(bytes_count: int) -> str:
    """Formate un nombre d'octets en format lisible"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} PB"

def _wait_for_job_completion(client: SaveOSAPIClient, job_id: int, timeout: int = 3600):
    """Attend la fin d'un job avec timeout"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        job_result = client.get_job_status(job_id)
        
        if job_result['success']:
            job_data = job_result['data']
            status = job_data['status']
            
            if status == 'completed':
                click.echo("✅ Sauvegarde terminée avec succès!")
                if job_data.get('snapshot_id'):
                    click.echo(f"   Snapshot ID: {job_data['snapshot_id']}")
                return
            elif status == 'failed':
                click.echo("❌ Sauvegarde échouée!")
                if job_data.get('error_message'):
                    click.echo(f"   Erreur: {job_data['error_message']}")
                return
            elif status == 'running':
                click.echo("⏳ Sauvegarde en cours...")
        else:
            click.echo(f"❌ Erreur lors de la vérification du job: {job_result['error']}")
            return
        
        time.sleep(10)  # Vérifier toutes les 10 secondes
    
    click.echo("⏰ Timeout atteint lors de l'attente du job")

if __name__ == '__main__':
    cli()