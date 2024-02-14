"""Code for interfacing with LDAP servers."""

from typing import List, Optional

import ldap3
from hpc_access_cli.config import LdapSettings
from hpc_access_cli.models import Gecos, LdapUser
from rich.console import Console

#: The rich console to use for output.
console = Console()


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
        console.log(f"Connecting to {self.server.host}:{self.server.port}...")
        #: Connection to the LDAP server.
        self.connection = ldap3.Connection(
            server=self.server,
            user=config.bind_dn,
            password=config.bind_pw.get_secret_value(),
            auto_bind=True,
        )
        if not self.connection.bind():
            raise Exception("Failed to bind to LDAP server.")
        console.log("... connected.")

    def load_users(self) -> List[LdapUser]:
        """Load ``LdapUser`` records from the LDAP server."""
        search_filter = "(&(objectClass=posixAccount)(uid=*))"

        console.log(f"Searching for users with filter {search_filter}...")
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
            uid_str = attribute_as_str(entry.uid)
            uid_number = int(uid_str) if uid_str else None
            if not uid_number:
                raise ValueError(f"Missing LDAP attribute uidNumber for {entry.dn}")
            gid_str = attribute_as_str(entry.gidNumber)
            gid_number = int(gid_str) if gid_str else None
            if not gid_number:
                raise ValueError(f"Missing LDAP attribute gidNumber for {entry.dn}")
            cn = attribute_as_str(entry.cn)
            if not cn:
                raise ValueError(f"Missing LDAP attribute cn for {entry.dn}")
            uid = attribute_as_str(entry.uid)
            if not uid:
                raise ValueError(f"Missing LDAP attribute uid for {entry.dn}")
            sn = attribute_as_str(entry.sn)
            if not sn:
                raise ValueError(f"Missing LDAP attribute sn for {entry.dn}")
            given_name = attribute_as_str(entry.givenName)
            if not given_name:
                raise ValueError(f"Missing LDAP attribute givenName for {entry.dn}")
            home_directory = attribute_as_str(entry.homeDirectory)
            if not home_directory:
                raise ValueError(f"Missing LDAP attribute homeDirectory for {entry.dn}")
            login_shell = attribute_as_str(entry.loginShell)
            if not login_shell:
                raise ValueError(f"Missing LDAP attribute loginShell for {entry.dn}")
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
