#!/usr/bin/env python3
"""
git-docker-worker-public.py

Fonctionnalités :
- Clone un repo Git
- Trouve le Dockerfile
- Build une image docker
- Crée un repo ECR Public (si absent)
- Tagge et push l'image
- Retourne le nom complet dans un fichier output.json

Prérequis :
- AWS creds exportés : AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
- Permissions IAM : ecr-public:* , sts:GetCallerIdentity
- Docker installé + accès au socket /var/run/docker.sock
"""

import os
import sys
import json
import argparse
import tempfile
import shutil
import subprocess
import logging
import base64
import boto3
import docker
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def run_cmd(cmd, cwd=None, check=True):
    p = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    logging.debug(p.stdout)
    if check and p.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nOutput:\n{p.stdout}")
    return p.stdout

def clone_repo(git_url, dest_dir):
    logging.info("Clonage du repo %s", git_url)
    run_cmd(["git", "clone", "--depth", "1", git_url, dest_dir])

def find_dockerfile(path):
    for root, dirs, files in os.walk(path):
        for name in files:
            if name.lower() == "dockerfile":
                return os.path.join(root, name)
    return None

def build_image(docker_client, context_path, dockerfile_path, full_tag):
    rel_path = os.path.relpath(dockerfile_path, context_path)
    logging.info("Construction de l'image avec Dockerfile=%s, tag=%s", rel_path, full_tag)
    image, logs = docker_client.images.build(path=context_path, dockerfile=rel_path, tag=full_tag, rm=True, pull=True)
    return image

def ensure_ecr_public_repo(ecr_pub_client, repo_name):
    try:
        resp = ecr_pub_client.describe_repositories(repositoryNames=[repo_name])
        uri = resp['repositories'][0]['repositoryUri']
        logging.info("Repo public déjà existant: %s", uri)
        return uri
    except ClientError as e:
        if e.response['Error']['Code'] == 'RepositoryNotFoundException':
            logging.info("Création du repo public %s", repo_name)
            resp = ecr_pub_client.create_repository(repositoryName=repo_name)
            return resp['repository']['repositoryUri']
        else:
            raise

def ecr_public_login_and_push(docker_client, ecr_pub_client, repo_uri, full_tag):
    # Récupérer un token d’auth
    auth = ecr_pub_client.get_authorization_token()
    auth_data = auth['authorizationData']
    token = auth_data['authorizationToken']
    endpoint = "public.ecr.aws"

    user_pass = base64.b64decode(token).decode("utf-8")
    user, password = user_pass.split(":", 1)

    logging.info("Connexion à ECR Public: %s", endpoint)
    docker_client.login(username=user, password=password, registry=endpoint)

    logging.info("Push de l'image %s", full_tag)
    for line in docker_client.images.push(repo_uri, tag=full_tag.split(":")[-1], stream=True, decode=True):
        logging.debug(line)
        if 'error' in line:
            raise RuntimeError("Erreur push: " + str(line))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--git-url", required=True)
    parser.add_argument("--repo-name", required=True, help="Nom du repository public ECR")
    parser.add_argument("--tag", default="latest")
    parser.add_argument("--output", default="output.json")
    args = parser.parse_args()

    tmpdir = tempfile.mkdtemp(prefix="git-docker-worker-")
    try:
        clone_repo(args.git_url, tmpdir)
        dockerfile = find_dockerfile(tmpdir)
        if not dockerfile:
            raise SystemExit("Aucun Dockerfile trouvé dans le repo.")
        logging.info("Dockerfile trouvé: %s", dockerfile)

        docker_client = docker.from_env()

        # Client ECR Public
        ecr_pub_client = boto3.client("ecr-public", region_name="us-east-1")

        # Crée ou récupère repo
        repo_uri = ensure_ecr_public_repo(ecr_pub_client, args.repo_name)

        # full tag ex: public.ecr.aws/<id>/<repo>:tag
        full_tag = f"{repo_uri}:{args.tag}"

        # Build + tag
        build_image(docker_client, tmpdir, dockerfile, full_tag)

        # Push
        ecr_public_login_and_push(docker_client, ecr_pub_client, repo_uri, full_tag)

        # Résultat JSON
        result = {"image": full_tag}
        with open(args.output, "w") as f:
            json.dump(result, f)
        logging.info("Image poussée: %s", full_tag)
        logging.info("Résultat écrit dans %s", args.output)

    except Exception as e:
        logging.exception("Erreur: %s", e)
        sys.exit(1)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

if __name__ == "__main__":
    main()
