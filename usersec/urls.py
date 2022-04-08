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
    # HpcGroupChangeRequest related
    # ------------------------------------------------------------------------------
    path(
        "hpcgroup/<uuid:hpcgroup>/hpcgroupchangerequest/",
        view=views.HpcGroupChangeRequestCreateView.as_view(),
        name="hpcgroupchangerequest-create",
    ),
    path(
        "hpcgroupchangerequest/<uuid:hpcgroupchangerequest>/detail/",
        view=views.HpcGroupChangeRequestDetailView.as_view(),
        name="hpcgroupchangerequest-detail",
    ),
    path(
        "hpcgroupchangerequest/<uuid:hpcgroupchangerequest>/update/",
        view=views.HpcGroupChangeRequestUpdateView.as_view(),
        name="hpcgroupchangerequest-update",
    ),
    path(
        "hpcgroupchangerequest/<uuid:hpcgroupchangerequest>/retract/",
        view=views.HpcGroupChangeRequestRetractView.as_view(),
        name="hpcgroupchangerequest-retract",
    ),
    path(
        "hpcgroupchangerequest/<uuid:hpcgroupchangerequest>/reactivate/",
        view=views.HpcGroupChangeRequestReactivateView.as_view(),
        name="hpcgroupchangerequest-reactivate",
    ),
    # ------------------------------------------------------------------------------
    # HpcGroupDeleteRequest related
    # ------------------------------------------------------------------------------
    path(
        "hpcgroup/<uuid:hpcgroup>/hpcgroupdeleterequest/",
        view=views.HpcGroupDeleteRequestCreateView.as_view(),
        name="hpcgroupdeleterequest-create",
    ),
    path(
        "hpcgroupdeleterequest/<uuid:hpcgroupdeleterequest>/detail/",
        view=views.HpcGroupDeleteRequestDetailView.as_view(),
        name="hpcgroupdeleterequest-detail",
    ),
    path(
        "hpcgroupdeleterequest/<uuid:hpcgroupdeleterequest>/update/",
        view=views.HpcGroupDeleteRequestUpdateView.as_view(),
        name="hpcgroupdeleterequest-update",
    ),
    path(
        "hpcgroupdeleterequest/<uuid:hpcgroupdeleterequest>/retract/",
        view=views.HpcGroupDeleteRequestRetractView.as_view(),
        name="hpcgroupdeleterequest-retract",
    ),
    path(
        "hpcgroupdeleterequest/<uuid:hpcgroupdeleterequest>/reactivate/",
        view=views.HpcGroupDeleteRequestReactivateView.as_view(),
        name="hpcgroupdeleterequest-reactivate",
    ),
    # ------------------------------------------------------------------------------
    # HpcUser related
    # ------------------------------------------------------------------------------
    path(
        "hpcuser/<uuid:hpcuser>/overview/",
        view=views.HpcUserView.as_view(),
        name="hpcuser-overview",
    ),
    path(
        "hpcuser/<uuid:hpcuser>/detail/",
        view=views.HpcUserDetailView.as_view(),
        name="hpcuser-detail",
    ),
    # ------------------------------------------------------------------------------
    # HpcGroup related
    # ------------------------------------------------------------------------------
    path(
        "hpcgroup/<uuid:hpcgroup>/detail/",
        view=views.HpcGroupDetailView.as_view(),
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
    # ------------------------------------------------------------------------------
    # HpcUserChangeRequest related
    # ------------------------------------------------------------------------------
    path(
        "hpcgroup/<uuid:hpcgroup>/hpcuserchangerequest/",
        view=views.HpcUserChangeRequestCreateView.as_view(),
        name="hpcuserchangerequest-create",
    ),
    path(
        "hpcuserchangerequest/<uuid:hpcuserchangerequest>/detail/",
        view=views.HpcUserChangeRequestDetailView.as_view(),
        name="hpcuserchangerequest-detail",
    ),
    path(
        "hpcuserchangerequest/<uuid:hpcuserchangerequest>/update/",
        view=views.HpcUserChangeRequestUpdateView.as_view(),
        name="hpcuserchangerequest-update",
    ),
    path(
        "hpcuserchangerequest/<uuid:hpcuserchangerequest>/retract/",
        view=views.HpcUserChangeRequestRetractView.as_view(),
        name="hpcuserchangerequest-retract",
    ),
    path(
        "hpcuserchangerequest/<uuid:hpcuserchangerequest>/reactivate/",
        view=views.HpcUserChangeRequestReactivateView.as_view(),
        name="hpcuserchangerequest-reactivate",
    ),
    # ------------------------------------------------------------------------------
    # HpcUserDeleteRequest related
    # ------------------------------------------------------------------------------
    path(
        "hpcgroup/<uuid:hpcgroup>/hpcuserdeleterequest/",
        view=views.HpcUserDeleteRequestCreateView.as_view(),
        name="hpcuserdeleterequest-create",
    ),
    path(
        "hpcuserdeleterequest/<uuid:hpcuserdeleterequest>/detail/",
        view=views.HpcUserDeleteRequestDetailView.as_view(),
        name="hpcuserdeleterequest-detail",
    ),
    path(
        "hpcuserdeleterequest/<uuid:hpcuserdeleterequest>/update/",
        view=views.HpcUserDeleteRequestUpdateView.as_view(),
        name="hpcuserdeleterequest-update",
    ),
    path(
        "hpcuserdeleterequest/<uuid:hpcuserdeleterequest>/retract/",
        view=views.HpcUserDeleteRequestRetractView.as_view(),
        name="hpcuserdeleterequest-retract",
    ),
    path(
        "hpcuserdeleterequest/<uuid:hpcuserdeleterequest>/reactivate/",
        view=views.HpcUserDeleteRequestReactivateView.as_view(),
        name="hpcuserdeleterequest-reactivate",
    ),
]
