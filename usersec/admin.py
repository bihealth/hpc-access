from django.contrib import admin  # noqa

from usersec.models import (
    HpcGroup,
    HpcGroupChangeRequest,
    HpcGroupChangeRequestVersion,
    HpcGroupCreateRequest,
    HpcGroupCreateRequestVersion,
    HpcGroupDeleteRequest,
    HpcGroupDeleteRequestVersion,
    HpcGroupVersion,
    HpcProject,
    HpcProjectChangeRequest,
    HpcProjectChangeRequestVersion,
    HpcProjectCreateRequest,
    HpcProjectCreateRequestVersion,
    HpcProjectDeleteRequest,
    HpcProjectDeleteRequestVersion,
    HpcProjectVersion,
    HpcUser,
    HpcUserChangeRequest,
    HpcUserChangeRequestVersion,
    HpcUserCreateRequest,
    HpcUserCreateRequestVersion,
    HpcUserDeleteRequest,
    HpcUserDeleteRequestVersion,
    HpcUserVersion,
)

# HpcUser related
# ------------------------------------------------------------------------------

admin.site.register(HpcUser)
admin.site.register(HpcUserVersion)

admin.site.register(HpcUserCreateRequest)
admin.site.register(HpcUserCreateRequestVersion)

admin.site.register(HpcUserChangeRequest)
admin.site.register(HpcUserChangeRequestVersion)

admin.site.register(HpcUserDeleteRequest)
admin.site.register(HpcUserDeleteRequestVersion)

# HpcGroup related
# ------------------------------------------------------------------------------

admin.site.register(HpcGroup)
admin.site.register(HpcGroupVersion)

admin.site.register(HpcGroupCreateRequest)
admin.site.register(HpcGroupCreateRequestVersion)

admin.site.register(HpcGroupChangeRequest)
admin.site.register(HpcGroupChangeRequestVersion)

admin.site.register(HpcGroupDeleteRequest)
admin.site.register(HpcGroupDeleteRequestVersion)

# HpcProject related
# ------------------------------------------------------------------------------

admin.site.register(HpcProject)
admin.site.register(HpcProjectVersion)

admin.site.register(HpcProjectCreateRequest)
admin.site.register(HpcProjectCreateRequestVersion)

admin.site.register(HpcProjectChangeRequest)
admin.site.register(HpcProjectChangeRequestVersion)

admin.site.register(HpcProjectDeleteRequest)
admin.site.register(HpcProjectDeleteRequestVersion)