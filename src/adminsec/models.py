from dataclasses import dataclass
from uuid import UUID

from usersec.models import HpcGroup, HpcProject, HpcUser

# Create your models here.


@dataclass(frozen=True)
class HpcaccessState:
    """Class to hold the status of the HPC access system."""

    hpc_users: dict[UUID, HpcUser]
    hpc_groups: dict[UUID, HpcGroup]
    hpc_projects: dict[UUID, HpcProject]
