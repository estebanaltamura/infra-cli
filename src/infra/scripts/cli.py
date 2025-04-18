import typer
from infra.scripts.create_env import run as create_env_run
# Placeholder para destroy
from infra.scripts.destroy_env import run as destroy_env_run  # (lo vas a crear ahora)

app = typer.Typer(help="CLI to manage ephemeral environments")

@app.command("create")
def create():
    """
    Creates an ephemeral development environment.
    """
    create_env_run()

@app.command("destroy")
def destroy():
    """
    Destroys an ephemeral development environment.
    """
    destroy_env_run()

if __name__ == "__main__":
    app()
