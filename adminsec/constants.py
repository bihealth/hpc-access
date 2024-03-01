# Collection of shared constants

POSIX_AG_PREFIX = "hpc-ag-"
POSIX_PRJ_PREFIX = "hpc-prj-"

LDAP_USERNAME_SEPARATOR = "@"
HPC_USERNAME_SEPARATOR = "_"

# Default values
DEFAULT_HOME_DIRECTORY = "/data/cephfs-1/home/users/{username}"
DEFAULT_GROUP_DIRECTORY = "/data/cephfs-1/work/groups/{group_name}"
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
