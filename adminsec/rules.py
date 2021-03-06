import rules

# ------------------------------------------------------------------------------
# Predicates
# ------------------------------------------------------------------------------


@rules.predicate
def is_hpcadmin(user):
    return user.is_hpcadmin


# ------------------------------------------------------------------------------
# Permissions
# ------------------------------------------------------------------------------


rules.add_perm("adminsec.is_hpcadmin", is_hpcadmin)
