# Collection of shared constants

POSIX_AG_PREFIX = "hpc-ag-"
POSIX_PROJECT_PREFIX = "hpc-prj-"

LDAP_USERNAME_SEPARATOR = "@"
HPC_USERNAME_SEPARATOR = "_"

# Default values
DEFAULT_HOME_DIRECTORY = "/data/cephfs-1/home/users/{username}"
DEFAULT_GROUP_DIRECTORY = "/data/cephfs-1/work/groups/{name}"
DEFAULT_PROJECT_DIRECTORY = "/data/cephfs-1/work/projects/{name}"
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
RE_PROJECT_NAME_CHECK = rf"^{POSIX_PROJECT_PREFIX}{RE_NAME_CORE}$"
RE_GROUP_NAME_CHECK = rf"^{POSIX_AG_PREFIX}{RE_NAME_CORE}$"
RE_FOLDER_CHECK = rf"^(/[a-zA-Z0-9-_]*)+{RE_NAME_CORE}$"
