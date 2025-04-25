import typer
from infra.scripts.create_backend import run as create_backend_run
from infra.scripts.destroy_env import run as destroy_env_run

app = typer.Typer(help="CLI to manage ephemeral dev environments.")

@app.command("create-backend")
def create_backend(
    is_ephemeral: bool = typer.Option(False, "--is-ephemeral", help="Whether the environment is ephemeral"),
    environment: str = typer.Option(None, "--environment", "-e", help="Define environment"),
    services: str = typer.Option(None, "--services", "-s", help="Comma-separated list of local services"),
):
    """
    Create an ephemeral environment.
    """
    create_backend_run(cli_environment=environment, cli_services=services, cli_is_ephemeral=is_ephemeral)

@app.command("destroy")
def destroy():
    """
    Destroy an ephemeral environment.
    """
    destroy_env_run()

if __name__ == "__main__":
    app()
