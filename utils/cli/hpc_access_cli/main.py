import typer
from hpc_access_cli.config import load_settings
from rich.console import Console
from typing_extensions import Annotated

#: The typer application object to use.
app = typer.Typer()
#: The rich console to use for output.
console = Console()


@app.command("send-welcome-email")
def send_welcome_email(
    email: Annotated[str, typer.Argument(..., help="recipient email address")],
    config_path: Annotated[
        str, typer.Option(..., help="path to configuration file")
    ] = "/etc/hpc-access-cli/config.json",
):
    """Send out welcome email to the given user."""
    settings = load_settings(config_path)
    _ = settings


if __name__ == "__main__":
    app()
