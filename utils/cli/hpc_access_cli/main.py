import sys
from typing import List, Optional

from hpc_access_cli.config import load_settings
from hpc_access_cli.models import StateOperation
from hpc_access_cli.states import (
    TargetStateBuilder,
    TargetStateComparison,
    convert_to_hpcaccess_state,
    gather_system_state,
)
from rich.console import Console
import typer
from typing_extensions import Annotated

#: The typer application object to use.
app = typer.Typer()
#: The rich console to use for output.
console_err = Console(file=sys.stderr)
console_out = Console(file=sys.stdout)


@app.command("record-usage")
def record_usage(
    config_path: Annotated[
        str, typer.Option(..., help="path to configuration file")
    ] = "/etc/hpc-access-cli/config.json",
):
    """record resource in hpc-access"""
    settings = load_settings(config_path)
    _ = settings


@app.command("dump")
def dump_data(
    config_path: Annotated[
        str, typer.Option(..., help="path to configuration file")
    ] = "/etc/hpc-access-cli/config.json"
):
    """dump system state as hpc-access state"""
    settings = load_settings(config_path)
    console_err.print_json(data=settings.model_dump(mode="json"))
    system_state = gather_system_state(settings)
    hpcaccess_state = convert_to_hpcaccess_state(system_state)
    console_out.print_json(data=hpcaccess_state.model_dump(mode="json"))


@app.command("sync")
def sync_data(
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
    dry_run: Annotated[bool, typer.Option(..., help="perform a dry run (no changes)")] = True,
    user_filter: Annotated[
        Optional[str], typer.Option(..., help="regex filter for users to sync (default: all)")
    ] = None,
    group_filter: Annotated[
        Optional[str], typer.Option(..., help="regex filter for groups to sync (default: all)")
    ] = None,
    fs_filter: Annotated[
        Optional[str],
        typer.Option(..., help="regex filter for file system folders to sync (default: all)"),
    ] = None,
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
    console_err.print_json(data=settings.model_dump(mode="json"))
    src_state = gather_system_state(settings)
    dst_builder = TargetStateBuilder(settings.hpc_access, src_state)
    dst_state = dst_builder.run()
    comparison = TargetStateComparison(settings.hpc_access, src_state, dst_state)
    operations = comparison.run()
    console_err.print_json(data=operations.model_dump(mode="json"))


if __name__ == "__main__":
    app()
