import rules

from config.settings.base import ENABLE_LDAP, ENABLE_LDAP_SECONDARY


# ------------------------------------------------------------------------------
# Predicates
# ------------------------------------------------------------------------------


@rules.predicate
def is_cluster_user(user):
    return user.hpcuser_user.exists()


@rules.predicate
def is_group_member(user, group):
    if is_cluster_user(user):
        return group.hpcuser.filter(user=user).exists()

    return False


@rules.predicate
def is_group_owner(user, group):
    if is_cluster_user(user):
        return user.hpcuser_user.filter(hpcgroup_owner=group).exists()

    return False


@rules.predicate
def is_group_delegate(user, group):
    if is_cluster_user(user):
        return user.hpcuser_user.filter(hpcgroup_delegate=group).exists()

    return False


@rules.predicate
def is_admin(user):
    domains = []

    if ENABLE_LDAP:
        from config.settings.base import AUTH_LDAP_USERNAME_DOMAIN

        domains.append(AUTH_LDAP_USERNAME_DOMAIN)

    if ENABLE_LDAP_SECONDARY:
        from config.settings.base import AUTH_LDAP2_USERNAME_DOMAIN

        domains.append(AUTH_LDAP2_USERNAME_DOMAIN)

    return user.is_superuser and not user.username.endswith(domains)


can_view_hpcgroup = is_group_owner | is_group_delegate | is_group_member
can_make_hpcgroup_request = is_group_owner | is_group_delegate
can_view_hpcuser = is_group_owner | is_group_delegate

# ------------------------------------------------------------------------------
# Permissions
# ------------------------------------------------------------------------------

rules.add_perm("usersec.view_hpcgroup", can_view_hpcgroup)
rules.add_perm("usersec.create_hpcgroupchangerequest", can_make_hpcgroup_request)
rules.add_perm("usersec.create_hpcgroupdeleterequest", can_make_hpcgroup_request)

rules.add_perm("usersec.view_hpcuser", can_view_hpcuser)
