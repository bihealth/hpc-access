import os
import re
import sys
from typing import List

from hpc_access_cli.config import load_settings
from hpc_access_cli.fs import FsResourceManager
from hpc_access_cli.ldap import LdapConnection
from hpc_access_cli.models import StateOperation
from hpc_access_cli.states import (
    POSIX_AG_PREFIX,
    POSIX_PROJECT_PREFIX,
    TargetStateBuilder,
    TargetStateComparison,
    convert_to_hpcaccess_state,
    deploy_hpcaccess_state,
    gather_hpcaccess_state,
    gather_system_state,
)
import mechanize
from rich.console import Console
import typer
from typing_extensions import Annotated

#: The typer application object to use.
app = typer.Typer()
#: The rich console to use for output.
console_err = Console(file=sys.stderr)
console_out = Console(file=sys.stdout)


@app.command("mailman-sync")
def mailman_sync(
    config_path: Annotated[
        str, typer.Option(..., help="path to configuration file")
    ] = "/etc/hpc-access-cli/config.json",
    dry_run: Annotated[bool, typer.Option(..., help="perform a dry run (no changes)")] = True,
):
    """obtain email addresses of active users and sync to mailman"""
    settings = load_settings(config_path)
    dst_state = gather_hpcaccess_state(settings.hpc_access)
    emails = list(sorted(user.email for user in dst_state.hpc_users.values() if user.email))
    console_err.log(f"will update to {len(emails)} email addresses")
    console_err.log("\n".join(emails))

    console_err.log(f"Opening URL to mailman '{settings.mailman.server_url}' ...")
    br = mechanize.Browser()
    br.set_handle_robots(False)
    br.open(str(settings.mailman.server_url))
    console_err.log("  ... filling login form")
    br.select_form(nr=0)
    br["adminpw"] = settings.mailman.admin_password.get_secret_value()
    console_err.log("  ... submitting login form")
    _ = br.submit()
    console_err.log("  ... filling sync membership list form")
    br.select_form(nr=0)
    br["memberlist"] = "\n".join(emails)
    if br.forms()[0].action != str(settings.mailman.server_url):  # type: ignore
        raise Exception(f"unexpected form action {br.forms()[0].action}")  # type: ignore
    console_err.log("  ... submitting sync membership list form")
    if dry_run:
        console_err.log("  ... **dry run, not submitting**")
    else:
        _ = br.submit()
    console_err.log("... done")


@app.command("state-dump")
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


@app.command("state-sync")
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
    # console_err.print_json(data=settings.model_dump(mode="json"))
    src_state = gather_system_state(settings)
    dst_builder = TargetStateBuilder(settings.hpc_access, src_state)
    dst_state = dst_builder.run()
    comparison = TargetStateComparison(settings.hpc_access, src_state, dst_state)
    operations = comparison.run()
    # console_err.print_json(data=operations.model_dump(mode="json"))
    connection = LdapConnection(settings.ldap_hpc)
    console_err.log(f"applying LDAP group operations now, dry_run={dry_run}")
    for group_op in operations.ldap_group_ops:
        connection.apply_group_op(group_op, dry_run)
    console_err.log(f"applying LDAP user operations now, dry_run={dry_run}")
    for user_op in operations.ldap_user_ops:
        connection.apply_user_op(user_op, dry_run)
    console_err.log(f"applying file system operations now, dry_run={dry_run}")
    fs_mgr = FsResourceManager(prefix="/data/sshfs" if os.environ.get("DEBUG", "0") == "1" else "")
    for fs_op in operations.fs_ops:
        fs_mgr.apply_fs_op(fs_op, dry_run)


RE_PATH = r"/(?P<tier>cephfs-[12])/(?P<subdir>[^/]+)/(?P<entity>[^/]+)/(?P<name>[^/]+)"
CEPHFS_TIER_MAPPING = {
    ("cephfs-1", "home", "users"): "tier1_home",
    ("cephfs-1", "work", "projects"): "tier1_work",
    ("cephfs-1", "work", "groups"): "tier1_work",
    ("cephfs-1", "scratch", "projects"): "tier1_scratch",
    ("cephfs-1", "scratch", "groups"): "tier1_scratch",
    ("cephfs-2", "unmirrored", "projects"): "tier2_unmirrored",
    ("cephfs-2", "unmirrored", "groups"): "tier2_unmirrored",
    ("cephfs-2", "mirrored", "projects"): "tier2_mirrored",
    ("cephfs-2", "mirrored", "groups"): "tier2_mirrored",
}


@app.command("storage-usage-sync")
def sync_storage_usage(
    config_path: Annotated[
        str, typer.Option(..., help="path to configuration file")
    ] = "/etc/hpc-access-cli/config.json",
    dry_run: Annotated[bool, typer.Option(..., help="perform a dry run (no changes)")] = True,
):
    """sync storage usage to hpc-access"""
    settings = load_settings(config_path)
    src_state = gather_system_state(settings)
    dst_state = gather_hpcaccess_state(settings.hpc_access)
    hpcaccess = {
        "groups": {},
        "projects": {},
        "users": {},
    }

    for entity in hpcaccess.keys():
        for d in getattr(dst_state, "hpc_%s" % entity).values():
            d.resources_used = {}
            name = d.username if entity == "users" else d.name
            hpcaccess[entity][name] = d

    for data in src_state.fs_directories.values():
        matches = re.search(RE_PATH, data.path)
        if not matches or matches.group("entity") not in ("users", "projects", "groups"):
            console_err.log("entity doesn't match:", matches.group("entity"))
            continue
        folder_name = matches.group("name")
        entity = matches.group("entity")
        if entity == "users":
            owner_name = data.owner_name
            if not owner_name or owner_name == "unknown":
                owner_name = folder_name
            elif not owner_name == folder_name:
                console_err.log(f"MISMATCH: {owner_name} {data.path}")
                continue
        elif entity == "projects":
            group_name = data.group_name
            if not group_name or group_name == "unknown":
                group_name = f"{POSIX_PROJECT_PREFIX}{folder_name}"
            elif not group_name == f"{POSIX_PROJECT_PREFIX}{folder_name}":
                console_err.log(f"MISMATCH: {group_name} {data.path}")
                continue
        elif entity == "groups":
            group_name = data.group_name
            folder_name = folder_name[3:] if folder_name.startswith("ag-") else folder_name
            if not group_name or group_name == "unknown":
                group_name = f"{POSIX_AG_PREFIX}{folder_name}"
            elif not group_name == f"{POSIX_AG_PREFIX}{folder_name}":
                console_err.log(f"MISMATCH: {group_name} {data.path}")
                continue
        entity = hpcaccess.get(entity, {}).get(folder_name)
        if not entity:
            console_err.log(
                f"CAN'T UPDATE (information not in hpc-access DB): {matches.group('entity')}/{folder_name}",
            )
            continue
        tier = CEPHFS_TIER_MAPPING.get(
            (matches.group("tier"), matches.group("subdir"), matches.group("entity"))
        )
        if not tier:
            console_err.log(
                f"path {data.path} not in {['/'.join(k) for k in CEPHFS_TIER_MAPPING.keys()]}"
            )
            continue
        d = getattr(dst_state, "hpc_%s" % matches.group("entity"))
        d[hpcaccess[matches.group("entity")][folder_name].uuid].resources_used[tier] = (
            data.rbytes / 1024**4
        )

    if not dry_run:
        deploy_hpcaccess_state(settings.hpc_access, dst_state)

    console_err.log(f"syncing storage usage to hpc-access now, dry_run={dry_run}")


if __name__ == "__main__":
    app()
