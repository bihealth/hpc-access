"""State gathering, comparison and update."""

import os
from typing import Dict

from hpc_access_cli.config import HpcaccessSettings, Settings
from hpc_access_cli.fs import FsResourceManager
from hpc_access_cli.ldap import LdapConnection
from hpc_access_cli.models import (
    Gecos,
    HpcaccessState,
    HpcUser,
    LdapGroup,
    LdapUser,
    SystemState,
)
from hpc_access_cli.rest import HpcaccessClient
from rich.console import Console

#: The rich console to use for output.
console = Console()

#: Base DN for work groups.
BASE_DN_GROUPS = "ou=Teams,ou=Groups,dc=hpc,dc=bihealth,dc=org"
#: Base DN for projects
BASE_DN_PROJECTS = "ou=Projects,ou=Groups,dc=hpc,dc=bihealth,dc=org"
#: Base DN for Charite users
BASE_DN_CHARITE = "ou=Charite,ou=Users,dc=hpc,dc=bihealth,dc=org"
#: Base DN for MDC users
BASE_DN_MDC = "ou=MDC,ou=Users,dc=hpc,dc=bihealth,dc=org"


def user_dn(user: HpcUser) -> str:
    """Get the DN for the user."""
    if user.username.endswith("_m"):
        return f"uid={user.full_name},{BASE_DN_MDC}"
    else:
        return f"uid={user.full_name},{BASE_DN_CHARITE}"


class TargetStateBuilder:
    """ "Helper class that is capable of building the target state giving data
    from hpc-access.
    """

    def __init__(self, settings: HpcaccessSettings):
        #: The settings to use.
        self.settings = settings

    def gather(self) -> HpcaccessState:
        """Gather the state."""
        console.log("Loading hpc-access users, groups, and projects...")
        rest_client = HpcaccessClient(self.settings)
        result = HpcaccessState(
            hpc_users={u.uuid: u for u in rest_client.load_users()},
            hpc_groups={g.uuid: g for g in rest_client.load_groups()},
            hpc_projects={p.uuid: p for p in rest_client.load_projects()},
        )
        console.log("  # of users:", len(result.hpc_users))
        console.log("  # of groups:", len(result.hpc_groups))
        console.log("  # of projects:", len(result.hpc_projects))
        console.log("... have hpc-access data now.")
        return result

    def build(self, hpcaccess_state: HpcaccessState) -> SystemState:
        """Build the target state."""
        return SystemState(
            ldap_users=self._build_ldap_users(hpcaccess_state),
            ldap_groups=self._build_ldap_groups(hpcaccess_state),
            fs_directories={},
        )

    def _build_ldap_users(self, hpcaccess_state: HpcaccessState) -> Dict[str, LdapUser]:
        """Build the LDAP users from the hpc-access state."""
        result = {}
        for user in hpcaccess_state.hpc_users.values():
            gecos = Gecos(
                full_name=user.full_name,
                office_location=None,
                office_phone=user.phone_number,
                other=None,
            )
            primary_group = hpcaccess_state.hpc_groups[user.primary_group]
            if not user.uid:
                console.log(
                    f"User {user.full_name} has no uid, skipping.",
                )
                continue
            if not primary_group.gid:
                console.log(
                    f"User {user.full_name} has no primary group, skipping.",
                )
                continue
            result[user.username] = LdapUser(
                dn=user_dn(user),
                cn=user.full_name,
                sn=user.last_name,
                given_name=user.first_name,
                uid=user.username,
                gecos=gecos,
                uid_number=user.uid,
                gid_number=primary_group.gid,
                home_directory=f"/data/cephfs-1/home/users/{user.username}",  # user.home_directory,
                login_shell="/usr/bin/bash",  # user.login_shell,
                # SSH keys are managed via upstream LDAP.
                ssh_public_key=[],
            )
        return result

    def _build_ldap_groups(self, state: HpcaccessState) -> Dict[str, LdapGroup]:
        """Build the LDAP groups from the hpc-access state."""
        result = {}
        # build for work groups
        for group in state.hpc_groups.values():
            if not group.gid:
                console.log(
                    f"Group {group.name} has no gid, skipping.",
                )
                continue
            group_dn = f"cn={group.name},{BASE_DN_GROUPS}"
            owner = state.hpc_users[group.owner]
            delegate = state.hpc_users[group.delegate] if group.delegate else None
            result[group.name] = LdapGroup(
                dn=group_dn,
                cn=group.name,
                gid_number=group.gid,
                owner_dn=user_dn(owner),
                delegate_dns=[user_dn(delegate)] if delegate else [],
                member_uids=[],
            )
        # build for projects
        for project in state.hpc_projects.values():
            if not project.gid:
                console.log(
                    f"Project {project.name} has no gid, skipping.",
                )
                continue
            group_dn = f"cn={project.name},{BASE_DN_PROJECTS}"
            owning_group = state.hpc_groups[project.group]
            owner = state.hpc_users[owning_group.owner]
            delegate = state.hpc_users[project.delegate] if project.delegate else None
            result[project.name] = LdapGroup(
                dn=group_dn,
                cn=project.name,
                gid_number=project.gid,
                owner_dn=user_dn(owner),
                delegate_dns=[user_dn(delegate)] if delegate else [],
                member_uids=[],
            )
        return result


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
    result = SystemState(
        ldap_users={u.uid: u for u in ldap_users},
        ldap_groups={g.cn: g for g in ldap_groups},
        fs_directories={d.path: d for d in fs_directories},
    )
    console.log("  # of users:", len(result.ldap_users))
    console.log("  # of groups:", len(result.ldap_groups))
    console.log("  # of directories:", len(result.fs_directories))
    console.log("... have system state now")
    return result
