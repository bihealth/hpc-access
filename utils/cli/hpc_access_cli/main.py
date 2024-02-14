import typer
from hpc_access_cli.config import load_settings
from hpc_access_cli.ldap import LdapConnection
from rich.console import Console
from typing_extensions import Annotated

#: The typer application object to use.
app = typer.Typer()
#: The rich console to use for output.
console = Console()


@app.command("record-usage")
def record_usage(
    config_path: Annotated[
        str, typer.Option(..., help="path to configuration file")
    ] = "/etc/hpc-access-cli/config.json",
):
    """record resource in hpc-access"""
    settings = load_settings(config_path)
    _ = settings
    #


@app.command("sync")
def sync(
    config_path: Annotated[
        str, typer.Option(..., help="path to configuration file")
    ] = "/etc/hpc-access-cli/config.json",
):
    """sync hpc-access state to HPC LDAP"""
    settings = load_settings(config_path)
    connection = LdapConnection(settings.ldap_hpc)
    # for user in connection.load_users():
    #     console.print_json(data=user.model_dump())
    for group in connection.load_groups():
        console.print_json(data=group.model_dump())


if __name__ == "__main__":
    app()
