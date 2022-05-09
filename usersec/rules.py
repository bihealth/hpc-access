import rules

from adminsec.rules import is_hpcadmin
from usersec.models import HpcGroupInvitation


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


@rules.predicate
def _has_group_invitation(user):
    return HpcGroupInvitation.objects.filter(username=user.username).exists()


has_pending_group_request = (
    ~is_hpcadmin & ~is_cluster_user & ~_has_group_invitation & _has_pending_group_request
)
is_orphan = ~is_hpcadmin & ~is_cluster_user & ~_has_group_invitation & ~_has_pending_group_request
has_group_invitation = ~is_hpcadmin & ~is_cluster_user & _has_group_invitation

can_create_hpcgroupcreaterequest = is_orphan


# HpcUser based
# ------------------------------------------------------------------------------


@rules.predicate
def _is_hpcuser(user, hpcuser):
    if hpcuser is None:
        return False

    return hpcuser.user == user


@rules.predicate
def _is_pi_of_hpcuser(user, hpcuser):
    if hpcuser is None:
        return False

    owner = hpcuser.primary_group.owner

    if owner:
        return owner.user == user

    return False


@rules.predicate
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


@rules.predicate
def _is_group_requester(user, hpcgroupcreaterequest):
    if hpcgroupcreaterequest is None:
        return False

    return hpcgroupcreaterequest.requester == user


is_group_requester = ~is_hpcadmin & ~is_cluster_user & _is_group_requester

can_view_hpcgroupcreaterequest = is_group_requester
can_manage_hpcgroupcreaterequest = is_group_requester


# Hpc*CreateRequest based
# ------------------------------------------------------------------------------


@rules.predicate
def _is_group_owner_by_createrequest(user, createrequest):
    if createrequest is None:
        return False

    owner = createrequest.group.owner

    if owner:
        return owner.user == user

    return False


@rules.predicate
def _is_group_delegate_by_createrequest(user, createrequest):
    if createrequest is None:
        return False

    delegate = createrequest.group.delegate

    if delegate:
        return delegate.user == user

    return False


is_group_owner_by_createrequest = ~is_hpcadmin & is_cluster_user & _is_group_owner_by_createrequest
is_group_delegate_by_createrequest = (
    ~is_hpcadmin & is_cluster_user & _is_group_delegate_by_createrequest
)

can_view_createrequest = is_group_owner_by_createrequest | is_group_delegate_by_createrequest
can_manage_createrequest = is_group_owner_by_createrequest | is_group_delegate_by_createrequest


# HpcGroup based
# ------------------------------------------------------------------------------


@rules.predicate
def _is_group_member(user, group):
    if group is None:
        return False

    return group.hpcuser.filter(user=user).exists()


@rules.predicate
def _is_group_owner(user, group):
    if group is None:
        return False

    return user.hpcuser_user.filter(hpcgroup_owner=group).exists()


@rules.predicate
def _is_group_delegate(user, group):
    if group is None:
        return False

    return user.hpcuser_user.filter(hpcgroup_delegate=group).exists()


is_group_member = ~is_hpcadmin & is_cluster_user & _is_group_member
is_group_owner = ~is_hpcadmin & is_cluster_user & _is_group_owner
is_group_delegate = ~is_hpcadmin & is_cluster_user & _is_group_delegate
is_group_manager = is_group_owner | is_group_delegate

can_view_hpcgroup = is_group_owner | is_group_delegate | is_group_member
can_create_createrequest = is_group_owner | is_group_delegate


# HpcProject based
# ------------------------------------------------------------------------------


@rules.predicate
def _is_project_member(user, project):
    if project is None:
        return False

    return project.members.contains(user.hpcuser_user.first())


@rules.predicate
def _is_project_owner(user, project):
    if project is None:
        return False

    return project.group.owner == user.hpcuser_user.first()


@rules.predicate
def _is_project_delegate(user, project):
    if project is None:
        return False

    return user.hpcuser_user.filter(hpcproject_delegate=project).exists()


is_project_member = ~is_hpcadmin & is_cluster_user & _is_project_member
is_project_owner = ~is_hpcadmin & is_cluster_user & _is_project_owner
is_project_delegate = ~is_hpcadmin & is_cluster_user & _is_project_delegate
is_project_manager = is_project_owner | is_project_delegate

can_view_hpcproject = is_project_owner | is_project_delegate | is_project_member


# HpcGroupInvitation based
# ------------------------------------------------------------------------------


@rules.predicate
def _is_group_invited_user(user, hpcgroupinvitation):
    if hpcgroupinvitation is None:
        return False

    return hpcgroupinvitation.username == user.username


can_manage_hpcgroupinvitation = ~is_hpcadmin & ~is_cluster_user & _is_group_invited_user


# HpcProjectInvitation based
# ------------------------------------------------------------------------------


@rules.predicate
def _is_project_invited_user(user, hpcprojectinvitation):
    if hpcprojectinvitation is None:
        return False

    return user.hpcuser_user.filter(id=hpcprojectinvitation.user.id).exists()


can_manage_hpcprojectinvitation = ~is_hpcadmin & is_cluster_user & _is_project_invited_user


# ------------------------------------------------------------------------------
# Rules
# ------------------------------------------------------------------------------


rules.add_rule("usersec.is_cluster_user", is_cluster_user)
rules.add_rule("usersec.has_pending_group_request", has_pending_group_request)
rules.add_rule("usersec.has_group_invitation", has_group_invitation)
rules.add_rule("usersec.is_group_manager", is_group_manager)
rules.add_rule("usersec.is_project_manager", is_project_manager)


# ------------------------------------------------------------------------------
# Permissions
# ------------------------------------------------------------------------------


# HpcUser related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.view_hpcuser", can_view_hpcuser)

# HpcUserCreateRequest related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.view_hpcusercreaterequest", can_view_createrequest)
rules.add_perm("usersec.create_hpcusercreaterequest", can_create_createrequest)
rules.add_perm("usersec.manage_hpcusercreaterequest", can_manage_createrequest)

# HpcGroup related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.view_hpcgroup", can_view_hpcgroup)

# HpcGroupCreateRequest related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.view_hpcgroupcreaterequest", can_view_hpcgroupcreaterequest)
rules.add_perm("usersec.create_hpcgroupcreaterequest", can_create_hpcgroupcreaterequest)
rules.add_perm("usersec.manage_hpcgroupcreaterequest", can_manage_hpcgroupcreaterequest)

# HpcProject related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.view_hpcproject", can_view_hpcproject)

# HpcProjectCreateRequest related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.view_hpcprojectcreaterequest", can_view_createrequest)
rules.add_perm("usersec.create_hpcprojectcreaterequest", can_create_createrequest)
rules.add_perm("usersec.manage_hpcprojectcreaterequest", can_manage_createrequest)

# HpcGroupInvitation related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.manage_hpcgroupinvitation", can_manage_hpcgroupinvitation)

# HpcProjectInvitation related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.manage_hpcprojectinvitation", can_manage_hpcprojectinvitation)
