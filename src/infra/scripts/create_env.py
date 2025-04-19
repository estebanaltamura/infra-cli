#!/usr/bin/env python3
"""
Script: create_env.py
---------------------
Creates an ephemeral environment by calling the Terraform service.
This script:
  - Loads environment variables using python-dotenv.
  - Gets the list of branches from the Terraform service.
  - Allows the user to choose a branch via console.
  - Prompts the user to choose which services to run locally.
  - Launches ngrok and gets the public endpoint.
  - Builds and sends a JSON payload to the Terraform endpoint.
"""

import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
import time


from infra.utils.ngrok_util import get_ngrok_endpoint


def get_repo_branches(terraform_endpoint_base):
    try:
        response = requests.get(f"{terraform_endpoint_base}/repos/branches")
        response.raise_for_status()
        data = response.json()
        return data.get("branches", [])
    except Exception as e:
        print(f"❌ Error fetching branches: {e}")
        return []


def choose_from_list(options, title="Choose one option"):
    if not options:
        print("⚠️ No options available.")
        sys.exit(1)

    print(f"\n📚 {title}:")
    for idx, opt in enumerate(options, 1):
        print(f"  {idx}. {opt}")

    while True:
        choice = input("👉 Choose (number or name): ").strip()
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        elif choice in options:
            return choice
        print("❌ Invalid option. Try again.")


def choose_multiple_from_list(options, title="Select one or more services"):
    if not options:
        print("⚠️ No services defined.")
        sys.exit(1)

    print(f"\n🧩 {title}:")
    for idx, opt in enumerate(options, 1):
        print(f"  {idx}. {opt}")

    while True:
        raw = input("👉 Enter numbers or names (comma-separated): ").strip()
        parts = [p.strip() for p in raw.split(",") if p.strip()]

        selected = []
        seen = set()
        all_valid = True

        for p in parts:
            if p in seen:
                print(f"❌ Duplicate entry detected: {p}")
                all_valid = False
                break
            seen.add(p)

            if p.isdigit():
                i = int(p)
                if 1 <= i <= len(options):
                    selected_name = options[i - 1]
                    if selected_name in selected:
                        print(f"❌ Duplicate service: {selected_name}")
                        all_valid = False
                        break
                    selected.append(selected_name)
                else:
                    print(f"❌ Invalid number: {p}")
                    all_valid = False
                    break
            elif p in options:
                if p in selected:
                    print(f"❌ Duplicate service: {p}")
                    all_valid = False
                    break
                selected.append(p)
            else:
                print(f"❌ Invalid name: {p}")
                all_valid = False
                break

        if all_valid and selected:
            return selected

        print("🔁 Please enter only valid, non-repeated names or numbers from the list.\n")





def build_payload(developer, local_services, ngrok_endpoint, selected_branch):
    return {
        "developer": developer,
        "local_services": local_services,
        "ngrok_endpoint": ngrok_endpoint,
        "branch": selected_branch,
    }


def send_payload(payload, terraform_endpoint):
    api_key = os.getenv("TERRAFORM_API_KEY")
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key
    }
    try:
        response = requests.post(terraform_endpoint, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        print("📦 Response from Terraform service:")
        print(json.dumps(response.json(), indent=2))
    except Exception as e:
        print(f"❌ Error sending payload: {e}")
        sys.exit(1)

def get_available_services(terraform_endpoint_base):
    try:
        res = requests.get(f"{terraform_endpoint_base}/services")
        res.raise_for_status()
        return res.json().get("services", [])
    except Exception as e:
        print(f"❌ Error fetching services: {e}")
        return []


def run(
    cli_services: str = None,
    cli_branch: str = None
):
    # 1. Cargar entorno
    env_file = find_dotenv(usecwd=True)
    load_dotenv(env_file, override=False)

    developer = os.getenv("DEVELOPER")
    terraform_endpoint = os.getenv("TERRAFORM_ENDPOINT")
    terraform_base = terraform_endpoint.rsplit("/", 1)[0]   

    if not terraform_endpoint:
        print("❌ TERRAFORM_ENDPOINT is not defined in env file")
        sys.exit(1)

    if not developer:
        print("❌ DEVELOPER is not defined in env file")
        sys.exit(1)

    # 2. Obtener opciones válidas
    print("🌐 Requesting availables services and availables branches")
    available_services = get_available_services(terraform_base)
    available_branches = get_repo_branches(terraform_base)

    # 3. Validar argumentos si fueron pasados
    if cli_services or cli_branch:
        if not (cli_services and cli_branch):
            print("❌ If you provide one of --services or --branch, you must provide both.")
            sys.exit(1)

        selected_branch = cli_branch.strip()
        if selected_branch not in available_branches:
            print(f"❌ Invalid branch: '{selected_branch}' not in available list.")
            sys.exit(1)

        local_services = [s.strip() for s in cli_services.split(",") if s.strip()]
        invalid_services = [s for s in local_services if s not in available_services]
        if invalid_services:
            print(f"❌ Invalid services: {', '.join(invalid_services)}")
            sys.exit(1)
    else:
        # Interactivo si no se pasaron argumentos
        local_services = choose_multiple_from_list(available_services, title="Select local services")
        selected_branch = choose_from_list(available_branches, title="Select a frontend branch to deploy")

    # 4. Iniciar ngrok
    try:
        print("🚀 Trying launch nrok")
        ngrok_endpoint = get_ngrok_endpoint()
    except RuntimeError as e:
        print(e)
        sys.exit(1)

    # 5. Confirmar
    print("\n📋 Verify your setup:")
    print(f"👤 Developer:       {developer}")
    print(f"🧩 Services:        {', '.join(local_services)}")
    print(f"🌿 Branch:          {selected_branch}")
    print(f"🌐 Ngrok endpoint:  {ngrok_endpoint}")

    while True:
        confirm = input("\n✅ Do you want to continue? (y/n): ").strip().lower()
        if confirm == "y":
            break
        elif confirm == "n":
            print("🚫 Operation cancelled by the user.")
            sys.exit(0)
        else:
            print("❌ Please respond with 'y' or 'n'.")

    # 6. Enviar
    payload = build_payload(developer, local_services, ngrok_endpoint, selected_branch)

    print("\n📤 Payload a enviar:")
    print(json.dumps(payload, indent=2))

    send_payload(payload, terraform_endpoint)

    print("\n✅ Environment created and running.")
    print("🔒 Press Ctrl+C to exit and shut down the environment.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Environment stopped.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--services", type=str, help="Comma-separated services")
    parser.add_argument("--branch", type=str, help="Branch to deploy")
    args = parser.parse_args()

    run(cli_services=args.services, cli_branch=args.branch)
