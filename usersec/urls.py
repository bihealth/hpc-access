from django.urls import path

from usersec import views

app_name = "usersec"


urlpatterns = [
    path("orphan/", view=views.OrphanUserView.as_view(), name="orphan-user"),
    # ------------------------------------------------------------------------------
    # HpcGroupCreateRequest related
    # ------------------------------------------------------------------------------
    path(
        "hpcgroupcreaterequest/<uuid:hpcgroupcreaterequest>/detail/",
        view=views.HpcGroupCreateRequestDetailView.as_view(),
        name="hpcgroupcreaterequest-detail",
    ),
    path(
        "hpcgroupcreaterequest/<uuid:hpcgroupcreaterequest>/update/",
        view=views.HpcGroupCreateRequestUpdateView.as_view(),
        name="hpcgroupcreaterequest-update",
    ),
    path(
        "hpcgroupcreaterequest/<uuid:hpcgroupcreaterequest>/retract/",
        view=views.HpcGroupCreateRequestRetractView.as_view(),
        name="hpcgroupcreaterequest-retract",
    ),
    path(
        "hpcgroupcreaterequest/<uuid:hpcgroupcreaterequest>/reactivate/",
        view=views.HpcGroupCreateRequestReactivateView.as_view(),
        name="hpcgroupcreaterequest-reactivate",
    ),
    # ------------------------------------------------------------------------------
    # HpcUser related
    # ------------------------------------------------------------------------------
    path(
        "hpcuser/<uuid:hpcuser>/overview/",
        view=views.HpcUserView.as_view(),
        name="hpcuser-overview",
    ),
    # ------------------------------------------------------------------------------
    # HpcGroup related
    # ------------------------------------------------------------------------------
    path(
        "hpcgroup/<uuid:hpcgroup>/detail/",
        view=views.HpcGroupView.as_view(),
        name="hpcgroup-detail",
    ),
    # ------------------------------------------------------------------------------
    # HpcUserCreateRequest related
    # ------------------------------------------------------------------------------
    path(
        "hpcgroup/<uuid:hpcgroup>/hpcusercreaterequest/",
        view=views.HpcUserCreateRequestCreateView.as_view(),
        name="hpcusercreaterequest-create",
    ),
    path(
        "hpcusercreaterequest/<uuid:hpcusercreaterequest>/detail/",
        view=views.HpcUserCreateRequestDetailView.as_view(),
        name="hpcusercreaterequest-detail",
    ),
    path(
        "hpcusercreaterequest/<uuid:hpcusercreaterequest>/update/",
        view=views.HpcUserCreateRequestUpdateView.as_view(),
        name="hpcusercreaterequest-update",
    ),
    path(
        "hpcusercreaterequest/<uuid:hpcusercreaterequest>/retract/",
        view=views.HpcUserCreateRequestRetractView.as_view(),
        name="hpcusercreaterequest-retract",
    ),
    path(
        "hpcusercreaterequest/<uuid:hpcusercreaterequest>/reactivate/",
        view=views.HpcUserCreateRequestReactivateView.as_view(),
        name="hpcusercreaterequest-reactivate",
    ),
]
