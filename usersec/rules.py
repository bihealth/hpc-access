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
can_create_hpcuserchangerequest = is_pi_of_hpcuser | is_delegate_of_hpcuser


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


# HpcGroupChangeRequest based
# ------------------------------------------------------------------------------


@rules.predicate
def _is_group_owner_by_hpcgroupchangerequest(user, hpcgroupchangerequest):
    if hpcgroupchangerequest is None:
        return False

    owner = hpcgroupchangerequest.group.owner

    if owner:
        return owner.user == user

    return False


@rules.predicate
def _is_group_delegate_by_hpcgroupchangerequest(user, hpcgroupchangerequest):
    if hpcgroupchangerequest is None:
        return False

    delegate = hpcgroupchangerequest.group.delegate

    if delegate:
        return delegate.user == user

    return False


is_group_owner_by_hpcgroupchangerequest = (
    ~is_hpcadmin & is_cluster_user & _is_group_owner_by_hpcgroupchangerequest
)
is_group_delegate_by_hpcgroupchangerequest = (
    ~is_hpcadmin & is_cluster_user & _is_group_delegate_by_hpcgroupchangerequest
)

can_view_hpcgroupchangerequest = (
    is_group_owner_by_hpcgroupchangerequest | is_group_delegate_by_hpcgroupchangerequest
)
can_manage_hpcgroupchangerequest = (
    is_group_owner_by_hpcgroupchangerequest | is_group_delegate_by_hpcgroupchangerequest
)


# HpcProjectCreateRequest based
# ------------------------------------------------------------------------------


@rules.predicate
def _is_group_owner_by_hpcprojectcreaterequest(user, hpcprojectcreaterequest):
    if hpcprojectcreaterequest is None:
        return False

    owner = hpcprojectcreaterequest.group.owner

    if owner:
        return owner.user == user

    return False


@rules.predicate
def _is_group_delegate_by_hpcprojectcreaterequest(user, hpcprojectcreaterequest):
    if hpcprojectcreaterequest is None:
        return False

    delegate = hpcprojectcreaterequest.group.delegate

    if delegate:
        return delegate.user == user

    return False


is_group_owner_by_hpcprojectcreaterequest = (
    ~is_hpcadmin & is_cluster_user & _is_group_owner_by_hpcprojectcreaterequest
)
is_group_delegate_by_hpcprojectcreaterequest = (
    ~is_hpcadmin & is_cluster_user & _is_group_delegate_by_hpcprojectcreaterequest
)

can_view_hpcprojectcreaterequest = (
    is_group_owner_by_hpcprojectcreaterequest | is_group_delegate_by_hpcprojectcreaterequest
)
can_manage_hpcprojectcreaterequest = (
    is_group_owner_by_hpcprojectcreaterequest | is_group_delegate_by_hpcprojectcreaterequest
)


# HpcProjectChangeRequest based
# ------------------------------------------------------------------------------


@rules.predicate
def _is_project_owner_by_hpcprojectchangerequest(user, hpcprojectchangerequest):
    if hpcprojectchangerequest is None:
        return False

    owner = hpcprojectchangerequest.project.group.owner

    if owner:
        return owner.user == user

    return False


@rules.predicate
def _is_project_delegate_by_hpcprojectchangerequest(user, hpcprojectchangerequest):
    if hpcprojectchangerequest is None:
        return False

    delegate = hpcprojectchangerequest.project.delegate

    if delegate:
        return delegate.user == user

    return False


is_project_owner_by_hpcprojectchangerequest = (
    ~is_hpcadmin & is_cluster_user & _is_project_owner_by_hpcprojectchangerequest
)
is_project_delegate_by_hpcprojectchangerequest = (
    ~is_hpcadmin & is_cluster_user & _is_project_delegate_by_hpcprojectchangerequest
)

can_view_hpcprojectchangerequest = (
    is_project_owner_by_hpcprojectchangerequest | is_project_delegate_by_hpcprojectchangerequest
)
can_manage_hpcprojectchangerequest = (
    is_project_owner_by_hpcprojectchangerequest | is_project_delegate_by_hpcprojectchangerequest
)


# HpcUserCreateRequest based
# ------------------------------------------------------------------------------


@rules.predicate
def _is_group_owner_by_hpcusercreaterequest(user, hpcusercreaterequest):
    if hpcusercreaterequest is None:
        return False

    owner = hpcusercreaterequest.group.owner

    if owner:
        return owner.user == user

    return False


@rules.predicate
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


# HpcUserChangeRequest based
# ------------------------------------------------------------------------------


@rules.predicate
def _is_group_owner_by_hpcuserchangerequest(user, hpcuserchangerequest):
    if hpcuserchangerequest is None:
        return False

    owner = hpcuserchangerequest.user.primary_group.owner

    if owner:
        return owner.user == user

    return False


@rules.predicate
def _is_group_delegate_by_hpcuserchangerequest(user, hpcuserchangerequest):
    if hpcuserchangerequest is None:
        return False

    delegate = hpcuserchangerequest.user.primary_group.delegate

    if delegate:
        return delegate.user == user

    return False


is_group_owner_by_hpcusercreaterequest = (
    ~is_hpcadmin & is_cluster_user & _is_group_owner_by_hpcuserchangerequest
)
is_group_delegate_by_hpcusercreaterequest = (
    ~is_hpcadmin & is_cluster_user & _is_group_delegate_by_hpcuserchangerequest
)

can_view_hpcuserchangerequest = (
    is_group_owner_by_hpcusercreaterequest | is_group_delegate_by_hpcusercreaterequest
)
can_manage_hpcuserchangerequest = (
    is_group_owner_by_hpcusercreaterequest | is_group_delegate_by_hpcusercreaterequest
)


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
can_create_hpcprojectcreaterequest = is_group_owner | is_group_delegate
can_create_hpcusercreaterequest = is_group_owner | is_group_delegate
can_create_hpcgroupchangerequest = is_group_owner | is_group_delegate


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
can_create_hpcprojectchangerequest = is_project_owner | is_project_delegate


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

rules.add_perm("usersec.view_hpcusercreaterequest", can_view_hpcusercreaterequest)
rules.add_perm("usersec.create_hpcusercreaterequest", can_create_hpcusercreaterequest)
rules.add_perm("usersec.manage_hpcusercreaterequest", can_manage_hpcusercreaterequest)

# HpcUserChangeRequest related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.view_hpcuserchangerequest", can_view_hpcuserchangerequest)
rules.add_perm("usersec.create_hpcuserchangerequest", can_create_hpcuserchangerequest)
rules.add_perm("usersec.manage_hpcuserchangerequest", can_manage_hpcuserchangerequest)

# HpcGroup related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.view_hpcgroup", can_view_hpcgroup)

# HpcGroupCreateRequest related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.view_hpcgroupcreaterequest", can_view_hpcgroupcreaterequest)
rules.add_perm("usersec.create_hpcgroupcreaterequest", can_create_hpcgroupcreaterequest)
rules.add_perm("usersec.manage_hpcgroupcreaterequest", can_manage_hpcgroupcreaterequest)

# HpcGroupChangeRequest related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.view_hpcgroupchangerequest", can_view_hpcgroupchangerequest)
rules.add_perm("usersec.create_hpcgroupchangerequest", can_create_hpcgroupchangerequest)
rules.add_perm("usersec.manage_hpcgroupchangerequest", can_manage_hpcgroupchangerequest)

# HpcProject related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.view_hpcproject", can_view_hpcproject)

# HpcProjectCreateRequest related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.view_hpcprojectcreaterequest", can_view_hpcprojectcreaterequest)
rules.add_perm("usersec.create_hpcprojectcreaterequest", can_create_hpcprojectcreaterequest)
rules.add_perm("usersec.manage_hpcprojectcreaterequest", can_manage_hpcprojectcreaterequest)

# HpcProjectChangeRequest related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.view_hpcprojectchangerequest", can_view_hpcprojectchangerequest)
rules.add_perm("usersec.create_hpcprojectchangerequest", can_create_hpcprojectchangerequest)
rules.add_perm("usersec.manage_hpcprojectchangerequest", can_manage_hpcprojectchangerequest)

# HpcGroupInvitation related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.manage_hpcgroupinvitation", can_manage_hpcgroupinvitation)

# HpcProjectInvitation related
# ------------------------------------------------------------------------------

rules.add_perm("usersec.manage_hpcprojectinvitation", can_manage_hpcprojectinvitation)
