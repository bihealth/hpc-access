from django.urls import path

from adminsec import views, views_api

app_name = "adminsec"


urlpatterns_ui = [
    path(
        "overview/",
        view=views.AdminView.as_view(),
        name="overview",
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
    # HpcUser related
    # ------------------------------------------------------------------------------
    path(
        "hpcuser/<uuid:hpcuser>/detail/",
        view=views.HpcUserDetailView.as_view(),
        name="hpcuser-detail",
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
    # ------------------------------------------------------------------------------
    # HpcProject related
    # ------------------------------------------------------------------------------
    path(
        "hpcproject/<uuid:hpcproject>/detail/",
        view=views.HpcProjectDetailView.as_view(),
        name="hpcproject-detail",
    ),
    # ------------------------------------------------------------------------------
    # HpcProjectCreateRequest related
    # ------------------------------------------------------------------------------
    path(
        "hpcprojectcreaterequest/<uuid:hpcprojectcreaterequest>/detail/",
        view=views.HpcProjectCreateRequestDetailView.as_view(),
        name="hpcprojectcreaterequest-detail",
    ),
    path(
        "hpcprojectcreaterequest/<uuid:hpcprojectcreaterequest>/revision/",
        view=views.HpcProjectCreateRequestRevisionView.as_view(),
        name="hpcprojectcreaterequest-revision",
    ),
    path(
        "hpcprojectcreaterequest/<uuid:hpcprojectcreaterequest>/approve/",
        view=views.HpcProjectCreateRequestApproveView.as_view(),
        name="hpcprojectcreaterequest-approve",
    ),
    path(
        "hpcprojectcreaterequest/<uuid:hpcprojectcreaterequest>/deny/",
        view=views.HpcProjectCreateRequestDenyView.as_view(),
        name="hpcprojectcreaterequest-deny",
    ),
    # ------------------------------------------------------------------------------
    # HpcProjectChangeRequest related
    # ------------------------------------------------------------------------------
    path(
        "hpcprojectchangerequest/<uuid:hpcprojectchangerequest>/detail/",
        view=views.HpcProjectChangeRequestDetailView.as_view(),
        name="hpcprojectchangerequest-detail",
    ),
    path(
        "hpcprojectchangerequest/<uuid:hpcprojectchangerequest>/revision/",
        view=views.HpcProjectChangeRequestRevisionView.as_view(),
        name="hpcprojectchangerequest-revision",
    ),
    path(
        "hpcprojectchangerequest/<uuid:hpcprojectchangerequest>/approve/",
        view=views.HpcProjectChangeRequestApproveView.as_view(),
        name="hpcprojectchangerequest-approve",
    ),
    path(
        "hpcprojectchangerequest/<uuid:hpcprojectchangerequest>/deny/",
        view=views.HpcProjectChangeRequestDenyView.as_view(),
        name="hpcprojectchangerequest-deny",
    ),
    # ------------------------------------------------------------------------------
    # HpcProjectDeleteRequest related
    # ------------------------------------------------------------------------------
    path(
        "hpcprojectdeleterequest/<uuid:hpcprojectdeleterequest>/detail/",
        view=views.HpcProjectDeleteRequestDetailView.as_view(),
        name="hpcprojectdeleterequest-detail",
    ),
    path(
        "hpcprojectdeleterequest/<uuid:hpcprojectdeleterequest>/revision/",
        view=views.HpcProjectDeleteRequestRevisionView.as_view(),
        name="hpcprojectdeleterequest-revision",
    ),
    path(
        "hpcprojectdeleterequest/<uuid:hpcprojectdeleterequest>/approve/",
        view=views.HpcProjectDeleteRequestApproveView.as_view(),
        name="hpcprojectdeleterequest-approve",
    ),
    path(
        "hpcprojectdeleterequest/<uuid:hpcprojectdeleterequest>/deny/",
        view=views.HpcProjectDeleteRequestDenyView.as_view(),
        name="hpcprojectdeleterequest-deny",
    ),
]

urlpatterns_api = [
    # API endpoints for HpcUser
    path(
        "api/hpcuser/",
        view=views_api.HpcUserListApiView.as_view(),
        name="api-hpcuser-list",
    ),
    path(
        "api/hpcuser/<uuid:hpcuser>/",
        view=views_api.HpcGroupRetrieveUpdateApiView.as_view(),
        name="api-hpcuser-retrieveupdate",
    ),
    # API endpoints for HpcGroup
    path(
        "api/hpcgroup/",
        view=views_api.HpcGroupListApiView.as_view(),
        name="api-hpcgroup-list",
    ),
    path(
        "api/hpcgroup/<uuid:hpcgroup>/",
        view=views_api.HpcGroupRetrieveUpdateApiView.as_view(),
        name="api-hpcgroup-retrieveupdate",
    ),
    # API endpoints for HpcProject
    path(
        "api/hpcproject/",
        view=views_api.HpcProjectListApiView.as_view(),
        name="api-hpcproject-list",
    ),
    path(
        "api/hpcproject/<uuid:hpcproject>/",
        view=views_api.HpcProjectRetrieveUpdateApiView.as_view(),
        name="api-hpcproject-retrieveupdate",
    ),
]

urlpatterns = urlpatterns_ui + urlpatterns_api
