# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot

snapshots = Snapshot()

snapshots["TestHpcGroupCreateRequestSerializer::testSerializerExisting 1"] = {
    "current_version": 1,
    "date_created": "2019-01-01T00:00:00Z",
    "description": "some group create request",
    "expiration": "2050-01-01T00:00:00Z",
    "folders": None,
    "name": None,
    "resources_requested": {"tier1": 0},
    "uuid": "uuid_placeholder",
}

snapshots["TestHpcGroupSerializer::testSerializerExisting 1"] = {
    "current_version": 1,
    "date_created": "2019-01-01T00:00:00Z",
    "delegate": None,
    "description": "this is a group",
    "expiration": "2050-01-01T00:00:00Z",
    "folders": {
        "tier1_scratch": "/data/scratch/group",
        "tier1_work": "/data/work/group",
        "tier2_mirrored": "/data/mirrored/group",
        "tier2_unmirrored": "/data/unmirrored/group",
    },
    "gid": 5000,
    "name": "group0",
    "owner": None,
    "resources_requested": {
        "tier1_scratch": 1,
        "tier1_work": 1,
        "tier2_mirrored": 0,
        "tier2_unmirrored": 0,
    },
    "resources_used": {
        "tier1_scratch": 0.5,
        "tier1_work": 0.5,
        "tier2_mirrored": 0,
        "tier2_unmirrored": 0,
    },
    "status": "INITIAL",
    "uuid": "uuid_placeholder",
}

snapshots["TestHpcGroupStatusSerializer::testSerializerExisting 1"] = {
    "delegate": None,
    "description": "this is a group",
    "expiration": "2050-01-01T00:00:00Z",
    "folders": {
        "tier1_scratch": "/data/scratch/group",
        "tier1_work": "/data/work/group",
        "tier2_mirrored": "/data/mirrored/group",
        "tier2_unmirrored": "/data/unmirrored/group",
    },
    "gid": 5000,
    "name": "group0",
    "owner": None,
    "resources_requested": {
        "tier1_scratch": 1,
        "tier1_work": 1,
        "tier2_mirrored": 0,
        "tier2_unmirrored": 0,
    },
    "status": "INITIAL",
}

snapshots["TestHpcProjectCreateRequestSerializer::testSerializerExisting 1"] = {
    "current_version": 1,
    "date_created": "2019-01-01T00:00:00Z",
    "description": "some description",
    "expiration": "2050-01-01T00:00:00Z",
    "folders": None,
    "group": "group_uuid_placeholder",
    "members": [],
    "name": None,
    "name_requested": "name_requested_placeholder",
    "resources_requested": {"null": "null"},
    "uuid": "uuid_placeholder",
}

snapshots["TestHpcProjectSerializer::testSerializerExisting 1"] = {
    "current_version": 1,
    "date_created": "2019-01-01T00:00:00Z",
    "delegate": None,
    "description": "this is a project",
    "expiration": "2050-01-01T00:00:00Z",
    "folders": {
        "tier1_scratch": "/data/scratch/project",
        "tier1_work": "/data/work/project",
        "tier2_mirrored": "/data/mirrored/project",
        "tier2_unmirrored": "/data/unmirrored/project",
    },
    "gid": 6000,
    "group": "group_uuid_placeholder",
    "members": [],
    "name": "hpc-project0",
    "resources_requested": {
        "tier1_scratch": 1,
        "tier1_work": 1,
        "tier2_mirrored": 0,
        "tier2_unmirrored": 0,
    },
    "resources_used": {
        "tier1_scratch": 0.5,
        "tier1_work": 0.5,
        "tier2_mirrored": 0,
        "tier2_unmirrored": 0,
    },
    "status": "INITIAL",
    "uuid": "uuid_placeholder",
}

snapshots["TestHpcProjectStatusSerializer::testSerializerExisting 1"] = {
    "delegate": None,
    "description": "this is a project",
    "expiration": "2050-01-01T00:00:00Z",
    "folders": {
        "tier1_scratch": "/data/scratch/project",
        "tier1_work": "/data/work/project",
        "tier2_mirrored": "/data/mirrored/project",
        "tier2_unmirrored": "/data/unmirrored/project",
    },
    "gid": 6000,
    "group": "group_name_placeholder",
    "members": [],
    "name": "hpc-project0",
    "resources_requested": {
        "tier1_scratch": 1,
        "tier1_work": 1,
        "tier2_mirrored": 0,
        "tier2_unmirrored": 0,
    },
    "status": "INITIAL",
}

snapshots["TestHpcUserSerializer::testSerializerExisting 1"] = {
    "current_version": 1,
    "date_created": "2019-01-01T00:00:00Z",
    "description": "this is a user",
    "display_name": None,
    "email": "email_placeholder",
    "expiration": "2050-01-01T00:00:00Z",
    "first_name": "first_name_placeholder",
    "full_name": "name_placeholder",
    "home_directory": "/data/cephfs-1/home/users/user0_c",
    "last_name": "last_name_placeholder",
    "login_shell": "/usr/bin/bash",
    "phone_number": "phone_number_placeholder",
    "primary_group": "primary_group_uuid_placeholder",
    "resources_requested": {"tier1_home": 1.0},
    "resources_used": {"tier1_home": 0.5},
    "status": "INITIAL",
    "uid": 2000,
    "username": "user0_c",
    "uuid": "uuid_placeholder",
}

snapshots["TestHpcUserStatusSerializer::testSerializerExisting 1"] = {
    "description": "this is a user",
    "email": "email_placeholder",
    "expiration": "2050-01-01T00:00:00Z",
    "first_name": "first_name_placeholder",
    "full_name": "name_placeholder",
    "home_directory": "/data/cephfs-1/home/users/user0_c",
    "last_name": "last_name_placeholder",
    "login_shell": "/usr/bin/bash",
    "phone_number": "phone_number_placeholder",
    "primary_group": "primary_group_name_placeholder",
    "resources_requested": {"tier1_home": 1.0},
    "status": "INITIAL",
    "uid": 2000,
    "username": "user0_c",
}
