from django.urls import path
from django.views.generic import TemplateView

from usersec import views, views_api

app_name = "usersec"


urlpatterns = [
    path("orphan/", view=views.OrphanUserView.as_view(), name="orphan-user"),
    path("terms/", view=views.TermsAndConditionsView.as_view(), name="terms"),
    path(
        "viewmode/",
        view=TemplateView.as_view(template_name="usersec/view_mode.html"),
        name="view-mode-enabled",
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
        "hpcgroupcreaterequest/<uuid:hpcgroupcreaterequest>/delete/",
        view=views.HpcGroupCreateRequestDeleteView.as_view(),
        name="hpcgroupcreaterequest-delete",
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
    path(
        "hpcgroupchangerequest/<uuid:hpcgroupchangerequest>/delete/",
        view=views.HpcGroupChangeRequestDeleteView.as_view(),
        name="hpcgroupchangerequest-delete",
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
    path(
        "hpcgroupdeleterequest/<uuid:hpcgroupdeleterequest>/delete/",
        view=views.HpcGroupDeleteRequestDeleteView.as_view(),
        name="hpcgroupdeleterequest-delete",
    ),
    # ------------------------------------------------------------------------------
    # HpcUser related
    # ------------------------------------------------------------------------------
    path(
        "",
        view=views.HpcUserView.as_view(),
        name="hpcuser-overview",
    ),
    path(  # TODO OBSOLETE
        "hpcuser/<uuid:hpcuser>/detail/",
        view=views.HpcUserDetailView.as_view(),
        name="hpcuser-detail",
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
    path(
        "hpcusercreaterequest/<uuid:hpcusercreaterequest>/delete/",
        view=views.HpcUserCreateRequestDeleteView.as_view(),
        name="hpcusercreaterequest-delete",
    ),
    # ------------------------------------------------------------------------------
    # HpcUserChangeRequest related
    # ------------------------------------------------------------------------------
    path(
        "hpcgroup/<uuid:hpcuser>/hpcuserchangerequest/",
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
    path(
        "hpcuserchangerequest/<uuid:hpcuserchangerequest>/delete/",
        view=views.HpcUserChangeRequestDeleteView.as_view(),
        name="hpcuserchangerequest-delete",
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
    path(
        "hpcuserdeleterequest/<uuid:hpcuserdeleterequest>/delete/",
        view=views.HpcUserDeleteRequestDeleteView.as_view(),
        name="hpcuserdeleterequest-delete",
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
        "hpcgroup/<uuid:hpcgroup>/hpcprojectcreaterequest/",
        view=views.HpcProjectCreateRequestCreateView.as_view(),
        name="hpcprojectcreaterequest-create",
    ),
    path(
        "hpcprojectcreaterequest/<uuid:hpcprojectcreaterequest>/detail/",
        view=views.HpcProjectCreateRequestDetailView.as_view(),
        name="hpcprojectcreaterequest-detail",
    ),
    path(
        "hpcprojectcreaterequest/<uuid:hpcprojectcreaterequest>/update/",
        view=views.HpcProjectCreateRequestUpdateView.as_view(),
        name="hpcprojectcreaterequest-update",
    ),
    path(
        "hpcprojectcreaterequest/<uuid:hpcprojectcreaterequest>/retract/",
        view=views.HpcProjectCreateRequestRetractView.as_view(),
        name="hpcprojectcreaterequest-retract",
    ),
    path(
        "hpcprojectcreaterequest/<uuid:hpcprojectcreaterequest>/reactivate/",
        view=views.HpcProjectCreateRequestReactivateView.as_view(),
        name="hpcprojectcreaterequest-reactivate",
    ),
    path(
        "hpcprojectcreaterequest/<uuid:hpcprojectcreaterequest>/delete/",
        view=views.HpcProjectCreateRequestDeleteView.as_view(),
        name="hpcprojectcreaterequest-delete",
    ),
    # ------------------------------------------------------------------------------
    # HpcProjectChangeRequest related
    # ------------------------------------------------------------------------------
    path(
        "hpcgroup/<uuid:hpcproject>/hpcprojectchangerequest/",
        view=views.HpcProjectChangeRequestCreateView.as_view(),
        name="hpcprojectchangerequest-create",
    ),
    path(
        "hpcprojectchangerequest/<uuid:hpcprojectchangerequest>/detail/",
        view=views.HpcProjectChangeRequestDetailView.as_view(),
        name="hpcprojectchangerequest-detail",
    ),
    path(
        "hpcprojectchangerequest/<uuid:hpcprojectchangerequest>/update/",
        view=views.HpcProjectChangeRequestUpdateView.as_view(),
        name="hpcprojectchangerequest-update",
    ),
    path(
        "hpcprojectchangerequest/<uuid:hpcprojectchangerequest>/retract/",
        view=views.HpcProjectChangeRequestRetractView.as_view(),
        name="hpcprojectchangerequest-retract",
    ),
    path(
        "hpcprojectchangerequest/<uuid:hpcprojectchangerequest>/reactivate/",
        view=views.HpcProjectChangeRequestReactivateView.as_view(),
        name="hpcprojectchangerequest-reactivate",
    ),
    path(
        "hpcprojectchangerequest/<uuid:hpcprojectchangerequest>/delete/",
        view=views.HpcProjectChangeRequestDeleteView.as_view(),
        name="hpcprojectchangerequest-delete",
    ),
    # ------------------------------------------------------------------------------
    # HpcProjectDeleteRequest related
    # ------------------------------------------------------------------------------
    path(
        "hpcgroup/<uuid:hpcgroup>/hpcprojectdeleterequest/",
        view=views.HpcProjectDeleteRequestCreateView.as_view(),
        name="hpcprojectdeleterequest-create",
    ),
    path(
        "hpcprojectdeleterequest/<uuid:hpcprojectdeleterequest>/detail/",
        view=views.HpcProjectDeleteRequestDetailView.as_view(),
        name="hpcprojectdeleterequest-detail",
    ),
    path(
        "hpcprojectdeleterequest/<uuid:hpcprojectdeleterequest>/update/",
        view=views.HpcProjectDeleteRequestUpdateView.as_view(),
        name="hpcprojectdeleterequest-update",
    ),
    path(
        "hpcprojectdeleterequest/<uuid:hpcprojectdeleterequest>/retract/",
        view=views.HpcProjectDeleteRequestRetractView.as_view(),
        name="hpcprojectdeleterequest-retract",
    ),
    path(
        "hpcprojectdeleterequest/<uuid:hpcprojectdeleterequest>/reactivate/",
        view=views.HpcProjectDeleteRequestReactivateView.as_view(),
        name="hpcprojectdeleterequest-reactivate",
    ),
    path(
        "hpcprojectdeleterequest/<uuid:hpcprojectdeleterequest>/delete/",
        view=views.HpcProjectDeleteRequestDeleteView.as_view(),
        name="hpcprojectdeleterequest-delete",
    ),
    # ------------------------------------------------------------------------------
    # HpcGroupInvitation related
    # ------------------------------------------------------------------------------
    path(
        "hpcgroupinvitation/<uuid:hpcgroupinvitation>/detail/",
        view=views.HpcGroupInvitationDetailView.as_view(),
        name="hpcgroupinvitation-detail",
    ),
    path(
        "hpcgroupinvitation/<uuid:hpcgroupinvitation>/accept/",
        view=views.HpcGroupInvitationAcceptView.as_view(),
        name="hpcgroupinvitation-accept",
    ),
    path(
        "hpcgroupinvitation/<uuid:hpcgroupinvitation>/reject/",
        view=views.HpcGroupInvitationRejectView.as_view(),
        name="hpcgroupinvitation-reject",
    ),
    # ------------------------------------------------------------------------------
    # HpcProjectInvitation related
    # ------------------------------------------------------------------------------
    path(
        "hpcprojectinvitation/<uuid:hpcprojectinvitation>/accept/",
        view=views.HpcProjectInvitationAcceptView.as_view(),
        name="hpcprojectinvitation-accept",
    ),
    path(
        "hpcprojectinvitation/<uuid:hpcprojectinvitation>/reject/",
        view=views.HpcProjectInvitationRejectView.as_view(),
        name="hpcprojectinvitation-reject",
    ),
    # ------------------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------------------
    path(
        "api/hpcuser/lookup/",
        view=views_api.HpcUserLookupApiView.as_view(),
        name="api-hpcuser-lookup",
    ),
]
