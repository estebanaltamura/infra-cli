import typer
from infra.scripts.create_env import run as create_env_run

app = typer.Typer()

@app.command("create-env")
def create_env(    
):   
    create_env_run()

if __name__ == "__main__":
    app()
