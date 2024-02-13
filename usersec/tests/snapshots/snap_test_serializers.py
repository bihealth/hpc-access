# -*- coding: utf-8 -*-
# snapshottest: v1 - https://goo.gl/zC4yUc
from __future__ import unicode_literals

from snapshottest import Snapshot


snapshots = Snapshot()

snapshots['TestHpcGroupSerializer::testSerializeExisting 1'] = {
    'creator': None,
    'current_version': 1,
    'date_created': '2019-01-01T00:00:00Z',
    'delegate': None,
    'description': 'this is a group',
    'expiration': '2050-01-01T00:00:00Z',
    'folder': '/data/group',
    'gid': 2000,
    'name': 'hpc-group0',
    'owner': None,
    'resources_requested': {
        'tier1': 1,
        'tier2': 0
    },
    'resources_used': {
        'tier1': 0.5,
        'tier2': 0
    },
    'status': 'INITIAL',
    'uuid': 'uuid_placeholder'
}

snapshots['TestHpcProjectSerializer::testSerializeExisting 1'] = {
    'creator': None,
    'current_version': 1,
    'date_created': '2019-01-01T00:00:00Z',
    'delegate': None,
    'description': 'this is a project',
    'expiration': '2050-01-01T00:00:00Z',
    'folder': '/data/project',
    'gid': 5000,
    'name': 'hpc-project0',
    'resources_requested': {
        'null': 'null'
    },
    'resources_used': {
        'null': 'null'
    },
    'status': 'INITIAL',
    'uuid': 'uuid_placeholder'
}

snapshots['TestHpcUserSerializer::testSerializeExisting 1'] = {
    'creator': None,
    'current_version': 1,
    'date_created': '2019-01-01T00:00:00Z',
    'description': 'this is a user',
    'expiration': '2050-01-01T00:00:00Z',
    'primary_group': 'primary_group_uuid_placeholder',
    'resources_requested': {
        'null': 'null'
    },
    'resources_used': {
        'null': 'null'
    },
    'status': 'INITIAL',
    'uid': 2000,
    'user': None,
    'username': 'user0_c',
    'uuid': 'uuid_placeholder'
}
