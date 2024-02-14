import typer
from hpc_access_cli.config import load_settings
from hpc_access_cli.states import TargetStateBuilder, gather_system_state
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
):
    """sync hpc-access state to HPC LDAP"""
    settings = load_settings(config_path)
    system_state = gather_system_state(settings)
    console.print_json(data=system_state.model_dump())
    builder = TargetStateBuilder(settings.hpc_access, system_state)
    res = builder.build(builder.gather())
    console.print_json(data=res.model_dump())


if __name__ == "__main__":
    app()
