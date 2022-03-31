from django.urls import path

from usersec import views

app_name = "usersec"


urlpatterns = [
    path("orphan/", view=views.OrphanUserView.as_view(), name="orphan-user"),
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
    path(
        "hpcuser/<uuid:hpcuser>/overview/",
        view=views.HpcUserView.as_view(),
        name="hpcuser-overview",
    ),
    path(
        "hpcgroup/<uuid:hpcgroup>/detail/",
        view=views.HpcGroupView.as_view(),
        name="hpcgroup-detail",
    ),
]
