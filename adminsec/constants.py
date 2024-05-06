# Collection of shared constants

POSIX_AG_PREFIX = "hpc-ag-"
POSIX_PROJECT_PREFIX = "hpc-prj-"

LDAP_USERNAME_SEPARATOR = "@"
HPC_USERNAME_SEPARATOR = "_"

# Default values
DEFAULT_HOME_DIRECTORY = "/data/cephfs-1/home/users/{username}"
DEFAULT_GROUP_DIRECTORY_TIER1_WORK = "/data/cephfs-1/work/groups/{name}"
DEFAULT_GROUP_DIRECTORY_TIER1_SCRATCH = "/data/cephfs-1/scratch/groups/{name}"
DEFAULT_GROUP_DIRECTORY_TIER2_MIRRORED = "/data/cephfs-2/mirrored/groups/{name}"
DEFAULT_GROUP_DIRECTORY_TIER2_UNMIRRORED = "/data/cephfs-2/unmirrored/groups/{name}"
DEFAULT_PROJECT_DIRECTORY_TIER1_WORK = "/data/cephfs-1/work/projects/{name}"
DEFAULT_PROJECT_DIRECTORY_TIER1_SCRATCH = "/data/cephfs-1/scratch/projects/{name}"
DEFAULT_PROJECT_DIRECTORY_TIER2_MIRRORED = "/data/cephfs-2/mirrored/projects/{name}"
DEFAULT_PROJECT_DIRECTORY_TIER2_UNMIRRORED = "/data/cephfs-2/unmirrored/projects/{name}"
DEFAULT_USER_RESOURCES = {
    "tier1_scratch": 1,
    "tier1_work": 1,
    "tier2_mirrored": 0,
    "tier2_unmirrored": 0,
}
DEFAULT_GROUP_RESOURCES = {
    "tier1_scratch": 1,
    "tier1_work": 1,
    "tier2_mirrored": 0,
    "tier2_unmirrored": 0,
}
DEFAULT_PROJECT_RESOURCES = {
    "tier1_scratch": 1,
    "tier1_work": 1,
    "tier2_mirrored": 0,
    "tier2_unmirrored": 0,
}
RE_NAME_CORE = r"[a-z][a-z0-9-]*[a-z0-9]"
RE_NAME = rf"^{RE_NAME_CORE}$"
RE_FOLDER = rf"^(/[a-zA-Z0-9-_]*)+/(?P<name>{RE_NAME_CORE})$"
