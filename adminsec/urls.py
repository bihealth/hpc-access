from django.urls import path

from adminsec import views

app_name = "adminsec"


urlpatterns = [
    path(
        "overview/",
        view=views.AdminView.as_view(),
        name="overview",
    ),
    # ------------------------------------------------------------------------------
    # HpcGroupCreateRequest related
    # ------------------------------------------------------------------------------
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
    # ------------------------------------------------------------------------------
    # HpcUserCreateRequest related
    # ------------------------------------------------------------------------------
    path(
        "hpcusercreaterequest/<uuid:hpcusercreaterequest>/detail/",
        view=views.HpcUserCreateRequestDetailView.as_view(),
        name="hpcusercreaterequest-detail",
    ),
    path(
        "hpcusercreaterequest/<uuid:hpcusercreaterequest>/revision/",
        view=views.HpcUserCreateRequestRevisionView.as_view(),
        name="hpcusercreaterequest-revision",
    ),
    path(
        "hpcusercreaterequest/<uuid:hpcusercreaterequest>/approve/",
        view=views.HpcUserCreateRequestApproveView.as_view(),
        name="hpcusercreaterequest-approve",
    ),
    path(
        "hpcusercreaterequest/<uuid:hpcusercreaterequest>/deny/",
        view=views.HpcUserCreateRequestDenyView.as_view(),
        name="hpcusercreaterequest-deny",
    ),
]
