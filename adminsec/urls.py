from django.urls import path

from adminsec import views

app_name = "adminsec"


urlpatterns = [
    path(
        "overview/",
        view=views.AdminView.as_view(),
        name="overview",
    ),
    path(
        "hpcgroupcreaterequest/<uuid:hpcgroupcreaterequest>/detail/",
        view=views.HpcGroupCreateRequestDetailView.as_view(),
        name="hpcgroupcreaterequest-detail",
    ),
    path(
        "hpcgroupcreaterequest/<uuid:hpcgroupcreaterequest>/revision/",
        view=views.HpcGroupCreateRequestRevisionView.as_view(),
        name="hpcgroupcreaterequest-revision",
    ),
    path(
        "hpcgroupcreaterequest/<uuid:hpcgroupcreaterequest>/approve/",
        view=views.HpcGroupCreateRequestApproveView.as_view(),
        name="hpcgroupcreaterequest-approve",
    ),
    path(
        "hpcgroupcreaterequest/<uuid:hpcgroupcreaterequest>/deny/",
        view=views.HpcGroupCreateRequestDenyView.as_view(),
        name="hpcgroupcreaterequest-deny",
    ),
]
