import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
import time


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


def choose_multiple_services_from_list(options, title="Select one or more services"):
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





def build_payload(environment, services_to_deploy):
    return {
        "environment": environment,
        "services_to_deploy": services_to_deploy,
    }


def send_payload(payload, terraform_endpoint):
    headers = {
        "Content-Type": "application/json"}
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

def get_available_stable_environments(terraform_endpoint_base):
    try:
        res = requests.get(f"{terraform_endpoint_base}/available-stable-environments")
        res.raise_for_status()
        return res.json().get("available_stable_environments", [])
    except Exception as e:
        print(f"❌ Error fetching stable environments: {e}")
        return []


def run(
    cli_environment: str = None,
    cli_services: str = None,
    cli_is_ephemeral: bool = False,
):
    # 1. Load .env file
    env_file = find_dotenv(usecwd=True)
    load_dotenv(env_file, override=False)

    terraform_endpoint_base = os.getenv("TERRAFORM_ENDPOINT_BASE")
    terraform_create_ephemeral_endpoint = os.getenv("TERRAFORM_CREATE_EPHIMERAL_ENDPOINT")
    terraform_create_no_ephemeral_endpoint = os.getenv("TERRAFORM_CREATE_NO_EPHIMERAL_ENDPOINT")

    # Validar endpoints
    if not terraform_endpoint_base or not terraform_create_ephemeral_endpoint or not terraform_create_no_ephemeral_endpoint:
        print("❌ Missing required environment variables: TERRAFORM_ENDPOINT_BASE, TERRAFORM_CREATE_EPHIMERAL_ENDPOINT, or TERRAFORM_CREATE_NO_EPHIMERAL_ENDPOINT.")
        sys.exit(1)

    # 2. Obtener servicios y entornos estables    
    print("🌐 Requesting available services...")
    available_services = get_available_services(terraform_endpoint_base)

    print("🌐 Requesting available stable environments...")
    available_stable_environments = get_available_stable_environments(terraform_endpoint_base)  

    # 3. Decide mode: automatic or manual
    if cli_environment is not None and cli_services is not None and cli_is_ephemeral is not None:
        # ✅ Automatic mode
        environment = cli_environment
        is_ephemeral = cli_is_ephemeral        
        services_to_deploy = [s.strip() for s in cli_services.split(",") if s.strip()]        
    
    else:
        # 🛠️ Manual mode
        while True:
            ephemeral_input = input("Is this environment ephemeral? (y/n): ").strip().lower()
            if ephemeral_input in {"y", "n"}:
                is_ephemeral = ephemeral_input == "y"
                break
            print("❌ Please enter 'y' or 'n'.")
        
        print("📝 Enter environment name:")

        environment = input("Environment: ").strip()

        services_to_deploy = choose_multiple_services_from_list(
            available_services,
            title="Select services to deploy"
        )           

    # 4. Chequeo de entornos estables y servicios
    invalid_services = [s for s in services_to_deploy if s not in available_services]
    if invalid_services:
        print(f"❌ Invalid services: {', '.join(invalid_services)}")
        sys.exit(1)
    else:
        if(len(services_to_deploy) == 1):
            print("✅ The provided service is a valid service")
        else:
            print("✅ The provided services are valid services")

    if not is_ephemeral:
        if environment not in available_stable_environments:
            print(f"❌ Environment '{environment}' is not in this list of stable environments: {', '.join(available_stable_environments)}")
            sys.exit(1)
        else:
            print("✅ The provided environment is a valid stable environment")

    # 5. Confirm configuration
    print("\n📋 Review your configuration:")
    print(f"🧪  Ephemeral:           {'Yes' if is_ephemeral else 'No'}")
    print(f"🌍  Environment:         {environment}")
    print(f"🧩  Services to deploy:  {', '.join(services_to_deploy)}")

    while True:
        confirm = input("\n✅ Continue? (y/n): ").strip().lower()
        if confirm in {"y", "n"}:
            if confirm == "n":
                print("🚫 Operation cancelled by user.")
                sys.exit(0)
            break
        print("❌ Please enter 'y' or 'n'.")

    # 6. Build and send payload
    payload = build_payload(environment, services_to_deploy)

    print("\n📤 Sending payload:")
    print(json.dumps(payload, indent=2))

    endpoint = terraform_create_ephemeral_endpoint if is_ephemeral else terraform_create_no_ephemeral_endpoint
    send_payload(payload, endpoint)

    print("\n✅ Environment created and running.")
    print("🔒 Press Ctrl+C to exit and shut down the environment.")

    
