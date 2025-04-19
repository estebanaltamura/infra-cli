import typer
from infra.scripts.create_env import run as create_env_run
from infra.scripts.destroy_env import run as destroy_env_run

app = typer.Typer(help="CLI to manage ephemeral dev environments.")

@app.command("create")
def create(
    services: str = typer.Option(None, "--services", "-s", help="Comma-separated list of local services"),
    branch: str = typer.Option(None, "--branch", "-b", help="Git branch to deploy")
):
    """
    Create an ephemeral environment.
    """
    create_env_run(cli_services=services, cli_branch=branch)

@app.command("destroy")
def destroy():
    """
    Destroy an ephemeral environment.
    """
    destroy_env_run()

if __name__ == "__main__":
    app()
