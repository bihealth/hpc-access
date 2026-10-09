from django.contrib import admin  # noqa

from usersec.models import (
    HpcGroup,
    HpcGroupChangeRequest,
    HpcGroupCreateRequest,
    HpcGroupDeleteRequest,
    HpcProject,
    HpcProjectChangeRequest,
    HpcProjectCreateRequest,
    HpcProjectDeleteRequest,
    HpcUser,
    HpcUserChangeRequest,
    HpcUserCreateRequest,
    HpcUserDeleteRequest,
)

# HpcUser related
# ------------------------------------------------------------------------------

admin.site.register(HpcUser)

admin.site.register(HpcUserCreateRequest)

admin.site.register(HpcUserChangeRequest)

admin.site.register(HpcUserDeleteRequest)

# HpcGroup related
# ------------------------------------------------------------------------------

admin.site.register(HpcGroup)

admin.site.register(HpcGroupCreateRequest)

admin.site.register(HpcGroupChangeRequest)

admin.site.register(HpcGroupDeleteRequest)

# HpcProject related
# ------------------------------------------------------------------------------

admin.site.register(HpcProject)

admin.site.register(HpcProjectCreateRequest)

admin.site.register(HpcProjectChangeRequest)

admin.site.register(HpcProjectDeleteRequest)
