import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
import time
from infra.utils.ngrok_util import get_ngrok_endpoint


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





def build_payload(environment, services_to_deploy, ngrok_endpoint, is_ephemeral):
    return {
        "environment": environment,
        "services_to_deploy": services_to_deploy,
        "local_ip": ngrok_endpoint,
        "is_ephemeral": is_ephemeral
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
    cli_environment: str = None,
    cli_services: str = None,
    cli_is_ephemeral: bool = False,
):
    # 1. Load .env file
    env_file = find_dotenv(usecwd=True)
    load_dotenv(env_file, override=False)

    terraform_endpoint = os.getenv("TERRAFORM_ENDPOINT")
    if not terraform_endpoint:
        print("❌ TERRAFORM_ENDPOINT is not defined in the .env file.")
        sys.exit(1)

    terraform_base = terraform_endpoint.rsplit("/", 1)[0]

    print("🌐 Fetching available services...")
    available_services = get_available_services(terraform_base)

    # 2. Decide mode: automatic or manual
    if cli_environment and cli_services and cli_is_ephemeral is not None:
        # ✅ Automatic mode
        environment = cli_environment
        services_to_deploy = [s.strip() for s in cli_services.split(",") if s.strip()]
        invalid_services = [s for s in services_to_deploy if s not in available_services]

        if invalid_services:
            print(f"❌ Invalid services: {', '.join(invalid_services)}")
            sys.exit(1)

        is_ephemeral = cli_is_ephemeral
    else:
        # 🛠️ Manual mode
        print("📝 Enter environment name:")
        environment = input("Environment: ").strip()

        services_to_deploy = choose_multiple_services_from_list(available_services, title="Select services to deploy")

        while True:
            ephemeral_input = input("Is this environment ephemeral? (y/n): ").strip().lower()
            if ephemeral_input == "y":
                is_ephemeral = True
                break
            elif ephemeral_input == "n":
                is_ephemeral = False
                break
            else:
                print("❌ Please enter 'y' or 'n'.")

    # 3. Start ngrok
    try:
        print("🚀 Launching ngrok...")
        ngrok_endpoint = get_ngrok_endpoint()
    except RuntimeError as e:
        print(e)
        sys.exit(1)

    # 4. Confirm configuration
    print("\n📋 Review your configuration:")
    print(f"👤 Environment:         {environment}")
    print(f"🧩 Services to deploy:  {', '.join(services_to_deploy)}")
    print(f"🌐 Local ip:            {ngrok_endpoint}")
    print(f"🧪 Ephemeral:           {'Yes' if is_ephemeral else 'No'}")

    while True:
        confirm = input("\n✅ Continue? (y/n): ").strip().lower()
        if confirm == "y":
            break
        elif confirm == "n":
            print("🚫 Operation cancelled by user.")
            sys.exit(0)
        else:
            print("❌ Please enter 'y' or 'n'.")

    # 5. Build and send payload
    payload = build_payload(environment, services_to_deploy, ngrok_endpoint, is_ephemeral)

    print("\n📤 Sending payload:")
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

    parser = argparse.ArgumentParser(description="Create ephemeral environment")
    parser.add_argument("--services", type=str, help="Comma-separated list of services")
    parser.add_argument("--is-ephemeral", action="store_true", help="Flag to mark environment as ephemeral")

    args = parser.parse_args()

    run(
        cli_environment=args.branch,
        cli_services=args.services,
        cli_is_ephemeral=args.is_ephemeral
    )
