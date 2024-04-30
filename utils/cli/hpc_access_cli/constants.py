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
