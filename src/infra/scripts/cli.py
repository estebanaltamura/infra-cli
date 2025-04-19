import typer
from infra.scripts.create_env import run as create_env_run

app = typer.Typer()

@app.command("create-env")
def create_env(
    services: str = typer.Option(None, "--services", "-s", help="Comma-separated list of local services"),
    branch: str = typer.Option(None, "--branch", "-b", help="Git branch to deploy")
):
    """
    Crea un entorno efímero de desarrollo.
    """
    create_env_run(cli_services=services, cli_branch=branch)

if __name__ == "__main__":
    app()

