import rules

from adminsec.rules import is_hpcadmin


# ------------------------------------------------------------------------------
# Predicates
# ------------------------------------------------------------------------------


# Without object
# ------------------------------------------------------------------------------


@rules.predicate
def is_cluster_user(user):
    return user.hpcuser_user.exists()


@rules.predicate
def _has_pending_group_request(user):
    return user.hpcgroupcreaterequest_requester.exists()


# HpcUser object based
# ------------------------------------------------------------------------------


@rules.predicate
def _is_hpcuser(user, hpcuser):
    return hpcuser.user == user


@rules.predicate
def _is_pi_of_hpcuser(user, hpcuser):
    owner = hpcuser.primary_group.owner

    if owner:
        return owner.user == user

    return False


@rules.predicate
def _is_delegate_of_hpcuser(user, hpcuser):
    delegate = hpcuser.primary_group.delegate

    if delegate:
        return delegate.user == user

    return False


# HpcGroupCreateRequest object based
# ------------------------------------------------------------------------------


@rules.predicate
def _is_group_requester(user, hpcgroupcreaterequest):
    return hpcgroupcreaterequest.requester == user


# HpcGroup object based
# ------------------------------------------------------------------------------


@rules.predicate
def _is_group_member(user, group):
    return group.hpcuser.filter(user=user).exists()


@rules.predicate
def _is_group_owner(user, group):
    return user.hpcuser_user.filter(hpcgroup_owner=group).exists()


@rules.predicate
def _is_group_delegate(user, group):
    return user.hpcuser_user.filter(hpcgroup_delegate=group).exists()


has_pending_group_request = ~is_hpcadmin & ~is_cluster_user & _has_pending_group_request
is_orphan = ~is_hpcadmin & ~is_cluster_user & ~_has_pending_group_request
is_group_requester = ~is_hpcadmin & ~is_cluster_user & _is_group_requester
is_group_member = ~is_hpcadmin & is_cluster_user & _is_group_member
is_group_owner = ~is_hpcadmin & is_cluster_user & _is_group_owner
is_group_delegate = ~is_hpcadmin & is_cluster_user & _is_group_delegate
is_hpcuser = ~is_hpcadmin & is_cluster_user & _is_hpcuser
is_pi_of_hpcuser = ~is_hpcadmin & is_cluster_user & _is_pi_of_hpcuser
is_delegate_of_hpcuser = ~is_hpcadmin & is_cluster_user & _is_delegate_of_hpcuser

can_view_hpcgroup = is_group_owner | is_group_delegate | is_group_member
can_view_hpcgroupcreaterequest = is_group_requester
can_view_hpcgroupchangerequest = is_group_owner | is_group_delegate
can_view_hpcuser = is_hpcuser | is_pi_of_hpcuser | is_delegate_of_hpcuser
can_create_hpcgroupcreaterequest = is_orphan

# ------------------------------------------------------------------------------
# Rules
# ------------------------------------------------------------------------------


rules.add_rule("is_cluster_user", is_cluster_user)
rules.add_rule("has_pending_group_request", has_pending_group_request)


# ------------------------------------------------------------------------------
# Permissions
# ------------------------------------------------------------------------------


rules.add_perm("usersec.view_hpcgroup", can_view_hpcgroup)
rules.add_perm("usersec.view_hpcgroupcreaterequest", can_view_hpcgroupcreaterequest)
rules.add_perm("usersec.view_hpcuser", can_view_hpcuser)
rules.add_perm("usersec.create_hpcgroupcreaterequest", can_create_hpcgroupcreaterequest)
