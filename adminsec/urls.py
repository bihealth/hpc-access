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
    # HpcUser related
    # ------------------------------------------------------------------------------
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
    # HpcGroupChangeRequest related
    # ------------------------------------------------------------------------------
    path(
        "hpcgroupchangerequest/<uuid:hpcgroupchangerequest>/detail/",
        view=views.HpcGroupChangeRequestDetailView.as_view(),
        name="hpcgroupchangerequest-detail",
    ),
    path(
        "hpcgroupchangerequest/<uuid:hpcgroupchangerequest>/revision/",
        view=views.HpcGroupChangeRequestRevisionView.as_view(),
        name="hpcgroupchangerequest-revision",
    ),
    path(
        "hpcgroupchangerequest/<uuid:hpcgroupchangerequest>/approve/",
        view=views.HpcGroupChangeRequestApproveView.as_view(),
        name="hpcgroupchangerequest-approve",
    ),
    path(
        "hpcgroupchangerequest/<uuid:hpcgroupchangerequest>/deny/",
        view=views.HpcGroupChangeRequestDenyView.as_view(),
        name="hpcgroupchangerequest-deny",
    ),
    # ------------------------------------------------------------------------------
    # HpcGroupDeleteRequest related
    # ------------------------------------------------------------------------------
    path(
        "hpcgroupdeleterequest/<uuid:hpcgroupdeleterequest>/detail/",
        view=views.HpcGroupDeleteRequestDetailView.as_view(),
        name="hpcgroupdeleterequest-detail",
    ),
    path(
        "hpcgroupdeleterequest/<uuid:hpcgroupdeleterequest>/revision/",
        view=views.HpcGroupDeleteRequestRevisionView.as_view(),
        name="hpcgroupdeleterequest-revision",
    ),
    path(
        "hpcgroupdeleterequest/<uuid:hpcgroupdeleterequest>/approve/",
        view=views.HpcGroupDeleteRequestApproveView.as_view(),
        name="hpcgroupdeleterequest-approve",
    ),
    path(
        "hpcgroupdeleterequest/<uuid:hpcgroupdeleterequest>/deny/",
        view=views.HpcGroupDeleteRequestDenyView.as_view(),
        name="hpcgroupdeleterequest-deny",
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
    # ------------------------------------------------------------------------------
    # HpcUserChangeRequest related
    # ------------------------------------------------------------------------------
    path(
        "hpcuserchangerequest/<uuid:hpcuserchangerequest>/detail/",
        view=views.HpcUserChangeRequestDetailView.as_view(),
        name="hpcuserchangerequest-detail",
    ),
    path(
        "hpcuserchangerequest/<uuid:hpcuserchangerequest>/revision/",
        view=views.HpcUserChangeRequestRevisionView.as_view(),
        name="hpcuserchangerequest-revision",
    ),
    path(
        "hpcuserchangerequest/<uuid:hpcuserchangerequest>/approve/",
        view=views.HpcUserChangeRequestApproveView.as_view(),
        name="hpcuserchangerequest-approve",
    ),
    path(
        "hpcuserchangerequest/<uuid:hpcuserchangerequest>/deny/",
        view=views.HpcUserChangeRequestDenyView.as_view(),
        name="hpcuserchangerequest-deny",
    ),
    # ------------------------------------------------------------------------------
    # HpcUserDeleteRequest related
    # ------------------------------------------------------------------------------
    path(
        "hpcuserdeleterequest/<uuid:hpcuserdeleterequest>/detail/",
        view=views.HpcUserDeleteRequestDetailView.as_view(),
        name="hpcuserdeleterequest-detail",
    ),
    path(
        "hpcuserdeleterequest/<uuid:hpcuserdeleterequest>/revision/",
        view=views.HpcUserDeleteRequestRevisionView.as_view(),
        name="hpcuserdeleterequest-revision",
    ),
    path(
        "hpcuserdeleterequest/<uuid:hpcuserdeleterequest>/approve/",
        view=views.HpcUserDeleteRequestApproveView.as_view(),
        name="hpcuserdeleterequest-approve",
    ),
    path(
        "hpcuserdeleterequest/<uuid:hpcuserdeleterequest>/deny/",
        view=views.HpcUserDeleteRequestDenyView.as_view(),
        name="hpcuserdeleterequest-deny",
    ),
]
