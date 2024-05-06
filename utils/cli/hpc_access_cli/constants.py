#: Prefix for POSIX groups
POSIX_AG_PREFIX = "hpc-ag-"
#: Prefix for POSIX projects
POSIX_PROJECT_PREFIX = "hpc-prj-"

#: Base path for tier1
BASE_PATH_TIER1 = "/data/cephfs-1"
#: Base path for tier2
BASE_PATH_TIER2 = "/data/cephfs-2"

#: Base DN for work groups.
BASE_DN_GROUPS = "ou=Teams,ou=Groups,dc=hpc,dc=bihealth,dc=org"
#: Base DN for projects
BASE_DN_PROJECTS = "ou=Projects,ou=Groups,dc=hpc,dc=bihealth,dc=org"
#: Base DN for Charite users
BASE_DN_CHARITE = "ou=Charite,ou=Users,dc=hpc,dc=bihealth,dc=org"
#: Base DN for MDC users
BASE_DN_MDC = "ou=MDC,ou=Users,dc=hpc,dc=bihealth,dc=org"

#: Quota on user home (1G)
QUOTA_HOME_BYTES = 1024 * 1024 * 1024
#: Quota on scratch (100T)
QUOTA_SCRATCH_BYTES = 100 * 1024 * 1024 * 1024 * 1024

#: Group name for users without a group.
HPC_ALUMNIS_GROUP = "hpc-alumnis"
#: GID for users without a group.
HPC_ALUMNIS_GID = 1030001
#: Group name for hpc-users (active+has home)
HPC_USERS_GROUP = "hpc-users"
#: GID for hpc-users
HPC_USERS_GID = 1005269

ENTITY_USERS = "users"
ENTITY_GROUPS = "groups"
ENTITY_PROJECTS = "projects"
ENTITIES = (
    ENTITY_USERS,
    ENTITY_GROUPS,
    ENTITY_PROJECTS,
)

CEPHFS_TIER_MAPPING = {
    ("cephfs-1", "home", ENTITY_USERS): "tier1_home",
    ("cephfs-1", "work", ENTITY_PROJECTS): "tier1_work",
    ("cephfs-1", "work", ENTITY_GROUPS): "tier1_work",
    ("cephfs-1", "scratch", ENTITY_PROJECTS): "tier1_scratch",
    ("cephfs-1", "scratch", ENTITY_GROUPS): "tier1_scratch",
    ("cephfs-2", "unmirrored", ENTITY_PROJECTS): "tier2_unmirrored",
    ("cephfs-2", "unmirrored", ENTITY_GROUPS): "tier2_unmirrored",
    ("cephfs-2", "mirrored", ENTITY_PROJECTS): "tier2_mirrored",
    ("cephfs-2", "mirrored", ENTITY_GROUPS): "tier2_mirrored",
}
PREFIX_MAPPING = {
    "projects": POSIX_PROJECT_PREFIX,
    "groups": POSIX_AG_PREFIX,
}
RE_PATH = r"/(?P<tier>cephfs-[12])/(?P<subdir>[^/]+)/(?P<entity>[^/]+)/(?P<name>[^/]+)"
