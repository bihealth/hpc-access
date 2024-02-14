import os

import typer
from hpc_access_cli.config import Settings, load_settings
from hpc_access_cli.fs import FsResourceManager
from hpc_access_cli.ldap import LdapConnection
from hpc_access_cli.models import SystemState
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


def gather_system_state(settings: Settings) -> SystemState:
    """Gather the system state from LDAP and file system."""
    connection = LdapConnection(settings.ldap_hpc)
    console.log("Loading LDAP users and groups...")
    ldap_users = connection.load_users()
    ldap_groups = connection.load_groups()
    console.log("Loading file system directories...")
    fs_mgr = FsResourceManager(
        prefix="/data/sshfs" if os.environ.get("DEBUG", "0") == "1" else ""
    )
    fs_directories = fs_mgr.load_directories()
    console.log("... have system state now")
    return SystemState(
        ldap_users={u.dn: u for u in ldap_users},
        ldap_groups={g.dn: g for g in ldap_groups},
        fs_directories={d.path: d for d in fs_directories},
    )


@app.command("sync")
def sync(
    config_path: Annotated[
        str, typer.Option(..., help="path to configuration file")
    ] = "/etc/hpc-access-cli/config.json",
):
    """sync hpc-access state to HPC LDAP"""
    system_state = gather_system_state(load_settings(config_path))
    console.print_json(data=system_state.model_dump())


if __name__ == "__main__":
    app()
