from typing import List

import typer
from hpc_access_cli.config import load_settings
from hpc_access_cli.models import StateOperation
from hpc_access_cli.states import (
    TargetStateBuilder,
    TargetStateComparison,
    gather_system_state,
)
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


@app.command("sync")
def sync(
    config_path: Annotated[
        str, typer.Option(..., help="path to configuration file")
    ] = "/etc/hpc-access-cli/config.json",
    ldap_user_ops: Annotated[
        List[StateOperation],
        typer.Option(..., help="user operations to perform (default: all)"),
    ] = [],
    ldap_group_ops: Annotated[
        List[StateOperation],
        typer.Option(..., help="group operations to perform (default: all)"),
    ] = [],
    fs_ops: Annotated[
        List[StateOperation],
        typer.Option(..., help="file system operations to perform (default: all)"),
    ] = [],
    dry_run: Annotated[
        bool, typer.Option(..., help="perform a dry run (no changes)")
    ] = True,
):
    """sync hpc-access state to HPC LDAP"""
    settings = load_settings(config_path).model_copy(
        update={
            "ldap_user_ops": ldap_user_ops or list(StateOperation),
            "ldap_group_ops": ldap_group_ops or list(StateOperation),
            "fs_ops": fs_ops or list(StateOperation),
            "dry_run": dry_run,
        }
    )
    console.print_json(data=settings.model_dump(mode="json"))
    src_state = gather_system_state(settings)
    dst_builder = TargetStateBuilder(settings.hpc_access, src_state)
    dst_state = dst_builder.run()
    comparison = TargetStateComparison(settings.hpc_access, src_state, dst_state)
    operations = comparison.run()
    console.print_json(data=operations.model_dump(mode="json"))


if __name__ == "__main__":
    app()
