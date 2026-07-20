from dataclasses import dataclass

# Create your models here.


@dataclass(frozen=True)
class HpcAccessStatus:
    """Class to hold the status of the HPC access system."""

    hpc_users: list
    hpc_groups: list
    hpc_projects: list
