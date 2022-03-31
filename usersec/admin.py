from django.contrib import admin  # noqa

from usersec.models import (
    HpcUser,
    HpcGroup,
    HpcUserVersion,
    HpcGroupVersion,
    HpcGroupCreateRequestVersion,
    HpcGroupCreateRequest,
    HpcGroupChangeRequest,
    HpcGroupChangeRequestVersion,
    HpcGroupDeleteRequest,
    HpcGroupDeleteRequestVersion,
    HpcUserCreateRequest,
    HpcUserCreateRequestVersion,
    HpcUserChangeRequest,
    HpcUserChangeRequestVersion,
    HpcUserDeleteRequest,
    HpcUserDeleteRequestVersion,
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
