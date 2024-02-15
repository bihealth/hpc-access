"""Code for interfacing with LDAP servers."""

import sys
from typing import List, Optional

from hpc_access_cli.config import LdapSettings
from hpc_access_cli.models import Gecos, LdapGroup, LdapUser
import ldap3
from rich.console import Console

#: The rich console to use for output.
console_err = Console(file=sys.stderr)


def attribute_as_str(attribute: ldap3.Attribute) -> Optional[str]:
    """Get attribute as string or None if empty."""
    if len(attribute):
        return str(attribute[0])
    else:
        return None


def attribute_list_as_str_list(
    attribute: ldap3.Attribute,
) -> List[str]:
    """Get attribute as list of strings."""
    return [str(x) for x in attribute]


class LdapConnection:
    """Wrapper around an ``ldap3`` connection."""

    def __init__(self, config: LdapSettings):
        #: The configuration for the LDAP connection.
        self.config = config
        #: Server to connect to.
        self.server = ldap3.Server(
            host=config.server_host,
            port=config.server_port,
        )
        console_err.log(f"Connecting to {self.server.host}:{self.server.port}...")
        #: Connection to the LDAP server.
        self.connection = ldap3.Connection(
            server=self.server,
            user=config.bind_dn,
            password=config.bind_pw.get_secret_value(),
            auto_bind=True,
        )
        if not self.connection.bind():
            raise Exception("Failed to bind to LDAP server.")
        console_err.log("... connected.")

    def load_users(self) -> List[LdapUser]:
        """Load ``LdapUser`` records from the LDAP server."""
        search_filter = "(&(objectClass=posixAccount)(uid=*))"

        console_err.log(f"Searching for users with filter {search_filter}...")
        if not self.connection.search(
            search_base=self.config.search_base,
            search_filter=search_filter,
            search_scope=ldap3.SUBTREE,
            attributes=[
                "sn",
                "givenName",
                "cn",
                "uid",
                "uidNumber",
                "gidNumber",
                "homeDirectory",
                "gecos",
                "loginShell",
                "mail",
                "displayName",
                "sshPublicKey",
            ],
        ):
            raise Exception("Failed to search for users.")
        result = []
        for entry in self.connection.entries:
            gecos_str = attribute_as_str(entry.gecos)
            gecos = Gecos.from_string(gecos_str) if gecos_str else None
            uid_str = attribute_as_str(entry.uidNumber)
            uid_number = int(uid_str) if uid_str else None
            if not uid_number:
                raise ValueError(f"Missing LDAP attribute uidNumber for {entry.entry_dn}")
            gid_str = attribute_as_str(entry.gidNumber)
            gid_number = int(gid_str) if gid_str else None
            if not gid_number:
                raise ValueError(f"Missing LDAP attribute gidNumber for {entry.entry_dn}")
            cn = attribute_as_str(entry.cn)
            if not cn:
                raise ValueError(f"Missing LDAP attribute cn for {entry.entry_dn}")
            uid = attribute_as_str(entry.uid)
            if not uid:
                raise ValueError(f"Missing LDAP attribute uid for {entry.entry_dn}")
            sn = attribute_as_str(entry.sn)
            given_name = attribute_as_str(entry.givenName)
            home_directory = attribute_as_str(entry.homeDirectory)
            if not home_directory:
                raise ValueError(f"Missing LDAP attribute homeDirectory for {entry.entry_dn}")
            login_shell = attribute_as_str(entry.loginShell)
            if not login_shell:
                raise ValueError(f"Missing LDAP attribute loginShell for {entry.entry_dn}")
            result.append(
                LdapUser(
                    dn=entry.entry_dn,
                    cn=cn,
                    uid=uid,
                    sn=sn,
                    given_name=given_name,
                    uid_number=uid_number,
                    gid_number=gid_number,
                    home_directory=home_directory,
                    login_shell=login_shell,
                    gecos=gecos,
                    ssh_public_key=attribute_list_as_str_list(entry.sshPublicKey),
                )
            )
        return result

    def load_groups(self) -> List[LdapGroup]:
        """Load group names from the LDAP server."""
        search_filter = "(&(objectClass=posixGroup)(cn=*))"

        console_err.log(f"Searching for groups with filter {search_filter}...")
        if not self.connection.search(
            search_base=self.config.search_base,
            search_filter=search_filter,
            search_scope=ldap3.SUBTREE,
            attributes=[
                "cn",
                "gidNumber",
                "bih-groupOwnerDN",
                "bih-groupDelegateDNs",
                "memberUid",
            ],
        ):
            raise Exception("Failed to search for groups.")
        result = []
        for entry in self.connection.entries:
            cn = attribute_as_str(entry.cn)
            if not cn:
                raise ValueError(f"Missing LDAP attribute cn for {entry.entry_dn}")
            gid_str = attribute_as_str(entry.gidNumber)
            gid_number = int(gid_str) if gid_str else None
            if not gid_number:
                raise ValueError(f"Missing LDAP attribute gidNumber for {entry.entry_dn}")
            owner_dn = attribute_as_str(entry["bih-groupOwnerDN"])
            delegate_dns = attribute_list_as_str_list(entry["bih-groupDelegateDNs"])
            member_uids = attribute_list_as_str_list(entry.memberUid)
            result.append(
                LdapGroup(
                    dn=entry.entry_dn,
                    cn=cn,
                    gid_number=gid_number,
                    owner_dn=owner_dn,
                    delegate_dns=delegate_dns,
                    member_uids=member_uids,
                )
            )
        return result
