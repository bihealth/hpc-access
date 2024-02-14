# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot

snapshots = Snapshot()

snapshots["TestHpcGroupSerializer::testSerializeExisting 1"] = {
    "current_version": 1,
    "date_created": "2019-01-01T00:00:00Z",
    "delegate": None,
    "description": "this is a group",
    "expiration": "2050-01-01T00:00:00Z",
    "folder": "/data/group",
    "full_name": "name_placeholder",
    "gid": 2000,
    "name": "hpc-group0",
    "owner": None,
    "phone_number": "phone_number_placeholder",
    "resources_requested": {"tier1": 1, "tier2_mirrored": 0, "tier2_unmirrored": 0},
    "resources_used": {"tier1": 0.5, "tier2_mirrored": 0, "tier2_unmirrored": 0},
    "status": "INITIAL",
    "uuid": "uuid_placeholder",
}

snapshots["TestHpcProjectSerializer::testSerializeExisting 1"] = {
    "current_version": 1,
    "date_created": "2019-01-01T00:00:00Z",
    "delegate": None,
    "description": "this is a project",
    "expiration": "2050-01-01T00:00:00Z",
    "folder": "/data/project",
    "full_name": "name_placeholder",
    "gid": 5000,
    "group": "group_uuid_placeholder",
    "members": [],
    "name": "hpc-project0",
    "phone_number": "phone_number_placeholder",
    "resources_requested": {"null": "null"},
    "resources_used": {"null": "null"},
    "status": "INITIAL",
    "uuid": "uuid_placeholder",
}

snapshots["TestHpcUserSerializer::testSerializeExisting 1"] = {
    "current_version": 1,
    "date_created": "2019-01-01T00:00:00Z",
    "description": "this is a user",
    "expiration": "2050-01-01T00:00:00Z",
    "first_name": None,
    "full_name": "name_placeholder",
    "home_directory": "/data/cephfs-1/home/users/user0_c",
    "last_name": None,
    "login_shell": "/usr/bin/bash",
    "phone_number": "phone_number_placeholder",
    "primary_group": "primary_group_uuid_placeholder",
    "resources_requested": {"null": "null"},
    "resources_used": {"null": "null"},
    "status": "INITIAL",
    "uid": 2000,
    "username": "user0_c",
    "uuid": "uuid_placeholder",
}
