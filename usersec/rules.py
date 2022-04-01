import rules

from adminsec.rules import is_hpcadmin


# ------------------------------------------------------------------------------
# Predicates
# ------------------------------------------------------------------------------


# Without object
# ------------------------------------------------------------------------------


@rules.predicate  # noqa: E1101
def is_cluster_user(user):
    return user.hpcuser_user.exists()


@rules.predicate  # noqa: E1101
def _has_pending_group_request(user):
    return user.hpcgroupcreaterequest_requester.exists()


has_pending_group_request = ~is_hpcadmin & ~is_cluster_user & _has_pending_group_request
is_orphan = ~is_hpcadmin & ~is_cluster_user & ~_has_pending_group_request

can_create_hpcgroupcreaterequest = is_orphan


# HpcUser based
# ------------------------------------------------------------------------------


@rules.predicate  # noqa: E1101
def _is_hpcuser(user, hpcuser):
    if hpcuser is None:
        return False

    return hpcuser.user == user


@rules.predicate  # noqa: E1101
def _is_pi_of_hpcuser(user, hpcuser):
    if hpcuser is None:
        return False

    owner = hpcuser.primary_group.owner

    if owner:
        return owner.user == user

    return False


@rules.predicate  # noqa: E1101
def _is_delegate_of_hpcuser(user, hpcuser):
    if hpcuser is None:
        return False

    delegate = hpcuser.primary_group.delegate

    if delegate:
        return delegate.user == user

    return False


is_hpcuser = ~is_hpcadmin & is_cluster_user & _is_hpcuser
is_pi_of_hpcuser = ~is_hpcadmin & is_cluster_user & _is_pi_of_hpcuser
is_delegate_of_hpcuser = ~is_hpcadmin & is_cluster_user & _is_delegate_of_hpcuser

can_view_hpcuser = is_hpcuser | is_pi_of_hpcuser | is_delegate_of_hpcuser


# HpcGroupCreateRequest based
# ------------------------------------------------------------------------------


@rules.predicate  # noqa: E1101
def _is_group_requester(user, hpcgroupcreaterequest):
    if hpcgroupcreaterequest is None:
        return False

    return hpcgroupcreaterequest.requester == user


is_group_requester = ~is_hpcadmin & ~is_cluster_user & _is_group_requester

can_view_hpcgroupcreaterequest = is_group_requester
can_manage_hpcgroupcreaterequest = is_group_requester


# HpcUserCreateRequest based
# ------------------------------------------------------------------------------


@rules.predicate  # noqa: E1101
def _is_group_owner_by_hpcusercreaterequest(user, hpcusercreaterequest):
    if hpcusercreaterequest is None:
        return False

    owner = hpcusercreaterequest.group.owner

    if owner:
        return owner.user == user

    return False


@rules.predicate  # noqa: E1101
def _is_group_delegate_by_hpcusercreaterequest(user, hpcusercreaterequest):
    if hpcusercreaterequest is None:
        return False

    delegate = hpcusercreaterequest.group.delegate

    if delegate:
        return delegate.user == user

    return False


is_group_owner_by_hpcusercreaterequest = (
    ~is_hpcadmin & is_cluster_user & _is_group_owner_by_hpcusercreaterequest
)
is_group_delegate_by_hpcusercreaterequest = (
    ~is_hpcadmin & is_cluster_user & _is_group_delegate_by_hpcusercreaterequest
)

can_view_hpcusercreaterequest = (
    is_group_owner_by_hpcusercreaterequest | is_group_delegate_by_hpcusercreaterequest
)
can_manage_hpcusercreaterequest = (
    is_group_owner_by_hpcusercreaterequest | is_group_delegate_by_hpcusercreaterequest
)


# HpcGroup based
# ------------------------------------------------------------------------------


@rules.predicate  # noqa: E1101
def _is_group_member(user, group):
    if group is None:
        return False

    return group.hpcuser.filter(user=user).exists()


@rules.predicate  # noqa: E1101
def _is_group_owner(user, group):
    if group is None:
        return False

    return user.hpcuser_user.filter(hpcgroup_owner=group).exists()


@rules.predicate  # noqa: E1101
def _is_group_delegate(user, group):
    if group is None:
        return False

    return user.hpcuser_user.filter(hpcgroup_delegate=group).exists()


is_group_member = ~is_hpcadmin & is_cluster_user & _is_group_member
is_group_owner = ~is_hpcadmin & is_cluster_user & _is_group_owner
is_group_delegate = ~is_hpcadmin & is_cluster_user & _is_group_delegate
is_group_manager = is_group_owner | is_group_delegate

can_view_hpcgroup = is_group_owner | is_group_delegate | is_group_member
can_create_hpcusercreaterequest = is_group_owner | is_group_delegate


# ------------------------------------------------------------------------------
# Rules
# ------------------------------------------------------------------------------


rules.add_rule("usersec.is_cluster_user", is_cluster_user)  # noqa: E1101
rules.add_rule("usersec.has_pending_group_request", has_pending_group_request)  # noqa: E1101
rules.add_rule("usersec.is_group_manager", is_group_manager)  # noqa: E1101


# ------------------------------------------------------------------------------
# Permissions
# ------------------------------------------------------------------------------


# HpcUser related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.view_hpcuser", can_view_hpcuser)  # noqa: E1101

# HpcUserCreateRequest related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.view_hpcusercreaterequest", can_view_hpcusercreaterequest)  # noqa: E1101
rules.add_perm(
    "usersec.create_hpcusercreaterequest", can_create_hpcusercreaterequest
)  # noqa: E1101
rules.add_perm(
    "usersec.manage_hpcusercreaterequest", can_manage_hpcusercreaterequest
)  # noqa: E1101

# HpcGroup related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.view_hpcgroup", can_view_hpcgroup)  # noqa: E1101

# HpcGroupCreateRequest related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.view_hpcgroupcreaterequest", can_view_hpcgroupcreaterequest)  # noqa: E1101
rules.add_perm(
    "usersec.create_hpcgroupcreaterequest", can_create_hpcgroupcreaterequest
)  # noqa: E1101
rules.add_perm(
    "usersec.manage_hpcgroupcreaterequest", can_manage_hpcgroupcreaterequest
)  # noqa: E1101
