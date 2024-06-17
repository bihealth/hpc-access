import rules
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from django.views.generic.detail import SingleObjectMixin
from rules.contrib.views import PermissionRequiredMixin

from adminsec.constants import DEFAULT_HOME_DIRECTORY
from adminsec.email import (
    send_notification_admin_request,
    send_notification_manager_group_request,
    send_notification_manager_project_request,
    send_notification_manager_user_decided_invitation,
    send_notification_user_welcome_mail,
)
from usersec.forms import (
    HpcGroupChangeRequestForm,
    HpcGroupCreateRequestForm,
    HpcProjectChangeRequestForm,
    HpcProjectCreateRequestForm,
    HpcUserChangeRequestForm,
    HpcUserCreateRequestForm,
    ProjectSelectForm,
    UserSelectForm,
)
from usersec.models import (
    INVITATION_STATUS_ACCEPTED,
    INVITATION_STATUS_REJECTED,
    OBJECT_STATUS_ACTIVE,
    REQUEST_STATUS_ACTIVE,
    REQUEST_STATUS_REVISION,
    TERMS_AUDIENCE_ALL,
    TERMS_AUDIENCE_PI,
    TERMS_AUDIENCE_USER,
    HpcGroup,
    HpcGroupChangeRequest,
    HpcGroupCreateRequest,
    HpcGroupInvitation,
    HpcProject,
    HpcProjectChangeRequest,
    HpcProjectCreateRequest,
    HpcProjectInvitation,
    HpcUser,
    HpcUserChangeRequest,
    HpcUserCreateRequest,
    TermsAndConditions,
)

# -----------------------------------------------------------------------------
# UI messages
# -----------------------------------------------------------------------------

MSG_NO_AUTH = "User not authorized for requested action"
MSG_NO_AUTH_LOGIN = MSG_NO_AUTH + ", please log in"

MSG_PART_SUBMIT = "submit"
MSG_PART_SUBMITTED = "submitted"
MSG_PART_UPDATE = "update"
MSG_PART_UPDATED = "updated"
MSG_PART_RETRACT = "retract"
MSG_PART_RETRACTED = "retracted"
MSG_PART_REACTIVATE = "re-activate"
MSG_PART_REACTIVATED = "re-activated"
MSG_PART_GROUP_CREATION = "group creation"
MSG_PART_GROUP_UPDATE = "group update"
MSG_PART_GROUP_DELETION = "group deletion"
MSG_PART_USER_CREATION = "user creation"
MSG_PART_USER_UPDATE = "user update"
MSG_PART_USER_DELETION = "user deletion"
MSG_PART_PROJECT_CREATION = "project creation"
MSG_PART_PROJECT_UPDATE = "project update"
MSG_PART_PROJECT_DELETION = "project deletion"

MSG_REQUEST_FAILURE = "Couldn't {} request for {}."
MSG_REQUEST_SUCCESS = "Successfully {} request for {}."

MSG_INVITATION_SUPERUSER = (
    "Superuser is not allowed to accept invitations. This would lead to inconsistencies."
)
MSG_INVITATION_REJECTED_SUCCESS = "Invitation successfully rejected."
MSG_INVITATION_GROUP_USER_CREATE_FAILURE = "Could not create user: {}"
MSG_INVITATION_GROUP_USER_CREATE_SUCCESS = "Invitation successfully accepted and user created."
MSG_INVITATION_PROJECT_USER_ADD_FAILURE = "Could not add user to project: {}"
MSG_INVITATION_PROJECT_USER_ADD_SUCCESS = "Successfully joined the project."

MSG_TERMS_CONSENT = "Consented successfully to terms and conditions."


# -----------------------------------------------------------------------------
# Object comments
# -----------------------------------------------------------------------------

COMMENT_REACTIVATED = "Request re-activated"
COMMENT_RETRACTED = "Request retracted"


class HpcPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Customized required login and permission mixin."""

    def handle_no_permission(self):
        """Override to redirect user"""
        if self.request.user.is_authenticated:
            messages.error(self.request, MSG_NO_AUTH)
            return redirect(reverse("home"))

        else:
            messages.error(self.request, MSG_NO_AUTH_LOGIN)
            return redirect_to_login(self.request.get_full_path())


class HomeView(LoginRequiredMixin, View):
    """Home view."""

    def get(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return redirect(reverse("admin-landing"))

        if request.user.is_hpcadmin:
            return redirect(reverse("adminsec:overview"))

        if not request.user.consented_to_terms and get_terms_and_conditions(self.request).exists():
            return redirect(reverse("usersec:terms"))

        if rules.test_rule("usersec.is_cluster_user", request.user):
            return redirect(
                reverse(
                    "usersec:hpcuser-overview",
                    kwargs={"hpcuser": request.user.hpcuser_user.first().uuid},
                )
            )

        if settings.VIEW_MODE:
            return redirect(reverse("usersec:view-mode-enabled"))

        if rules.test_rule("usersec.has_pending_group_request", request.user):
            request_uuid = request.user.hpcgroupcreaterequest_requester.first().uuid
            return redirect(
                reverse(
                    "usersec:hpcgroupcreaterequest-detail",
                    kwargs={"hpcgroupcreaterequest": request_uuid},
                )
            )

        if rules.test_rule("usersec.has_group_invitation", request.user):
            invitation = HpcGroupInvitation.objects.get(username=request.user.username)
            return redirect(
                reverse(
                    "usersec:hpcgroupinvitation-detail",
                    kwargs={"hpcgroupinvitation": invitation.uuid},
                )
            )

        return redirect(reverse("usersec:orphan-user"))


class OrphanUserView(HpcPermissionMixin, CreateView):
    """Orphan user view."""

    template_name = "usersec/hpcgroupcreaterequest_form.html"
    form_class = HpcGroupCreateRequestForm
    permission_required = "usersec.create_hpcgroupcreaterequest"

    def get_success_url(self, uuid):
        return reverse(
            "usersec:hpcgroupcreaterequest-detail",
            kwargs={"hpcgroupcreaterequest": uuid},
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["terms_list"] = TermsAndConditions.objects.filter(
            audience=TERMS_AUDIENCE_PI, date_published__isnull=False
        )
        return context

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.requester = self.request.user
        obj.editor = self.request.user
        obj.status = REQUEST_STATUS_ACTIVE
        obj = obj.save_with_version()

        if not obj:
            messages.error(
                self.request, MSG_REQUEST_FAILURE.format(MSG_PART_SUBMIT, MSG_PART_GROUP_CREATION)
            )
            return HttpResponseRedirect(reverse("usersec:orphan-user"))

        if settings.SEND_EMAIL:
            send_notification_manager_group_request(obj)
            send_notification_admin_request(obj)

        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_SUBMITTED, MSG_PART_GROUP_CREATION)
        )
        return HttpResponseRedirect(self.get_success_url(obj.uuid))


class HpcGroupCreateRequestDetailView(HpcPermissionMixin, DetailView):
    """HPC group request detail view."""

    template_name = "usersec/hpcgroupcreaterequest_detail.html"
    model = HpcGroupCreateRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupcreaterequest"
    permission_required = "usersec.view_hpcgroupcreaterequest"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context["is_decided"] = obj.is_decided()
        context["is_denied"] = obj.is_denied()
        context["is_retracted"] = obj.is_retracted()
        context["is_approved"] = obj.is_approved()
        context["is_active"] = obj.is_active()
        context["is_revision"] = obj.is_revision()
        context["is_revised"] = obj.is_revised()
        return context


# TODO never used?
class HpcGroupCreateRequestUpdateView(HpcPermissionMixin, UpdateView):
    """HPC group create request update view."""

    template_name = "usersec/hpcgroupcreaterequest_form.html"
    model = HpcGroupCreateRequest
    form_class = HpcGroupCreateRequestForm
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupcreaterequest"
    permission_required = "usersec.manage_hpcgroupcreaterequest"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["update"] = True
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def get_success_url(self):
        return reverse(
            "usersec:hpcgroupcreaterequest-detail",
            kwargs={"hpcgroupcreaterequest": self.get_object().uuid},
        )

    def get_initial(self):
        initial = super().get_initial()
        initial["comment"] = ""
        return initial

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.editor = self.request.user
        status = obj.status

        if status == REQUEST_STATUS_REVISION:
            obj = obj.revised_with_version()

        else:
            obj = obj.save_with_version()

        if not obj:
            messages.error(
                self.request, MSG_REQUEST_FAILURE.format(MSG_PART_UPDATE, MSG_PART_GROUP_CREATION)
            )
            return HttpResponseRedirect(reverse("usersec:orphan-user"))

        # No email notification required
        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_UPDATED, MSG_PART_GROUP_CREATION)
        )
        return HttpResponseRedirect(self.get_success_url())


class HpcGroupCreateRequestRetractView(HpcPermissionMixin, DeleteView):
    """HPC group create request update view."""

    template_name_suffix = "_retract_confirm"
    model = HpcGroupCreateRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupcreaterequest"
    permission_required = "usersec.manage_hpcgroupcreaterequest"

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.comment = COMMENT_RETRACTED
        obj.editor = self.request.user
        obj.retract_with_version()

        # No email notification required
        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_RETRACTED, MSG_PART_GROUP_CREATION)
        )

        return HttpResponseRedirect(
            reverse(
                "usersec:hpcgroupcreaterequest-detail",
                kwargs={"hpcgroupcreaterequest": obj.uuid},
            )
        )


class HpcGroupCreateRequestReactivateView(HpcPermissionMixin, SingleObjectMixin, View):
    """HPC group create request update view."""

    model = HpcGroupCreateRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupcreaterequest"
    permission_required = "usersec.manage_hpcgroupcreaterequest"

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.status = REQUEST_STATUS_ACTIVE
        obj.comment = COMMENT_REACTIVATED
        obj.editor = self.request.user
        obj.save_with_version()

        if settings.SEND_EMAIL:
            send_notification_admin_request(obj)

        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_REACTIVATED, MSG_PART_GROUP_CREATION)
        )
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcgroupcreaterequest-detail",
                kwargs={"hpcgroupcreaterequest": obj.uuid},
            )
        )


class HpcUserView(HpcPermissionMixin, DetailView):
    """HPC user overview."""

    model = HpcUser
    template_name = "usersec/overview.html"
    slug_field = "uuid"
    slug_url_kwarg = "hpcuser"
    permission_required = "usersec.view_hpcuser"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = context["object"].primary_group
        is_group_manager = rules.test_rule("usersec.is_group_manager", self.request.user, group)
        is_project_manager = False

        for project in context["object"].hpcproject_delegate.all():
            is_project_manager |= rules.test_rule(
                "usersec.is_project_manager", self.request.user, project
            )

        context["group_manager"] = is_group_manager
        context["project_manager"] = is_project_manager
        context["view_mode"] = settings.VIEW_MODE
        projects_available = False

        if is_group_manager:
            context["hpcusercreaterequests"] = HpcUserCreateRequest.objects.filter(group=group)
            context["hpcprojectcreaterequests"] = HpcProjectCreateRequest.objects.filter(
                group=group
            )
            context["hpcuserchangerequests"] = HpcUserChangeRequest.objects.prefetch_related(
                "user"
            ).filter(user__primary_group=group)
            context["hpcgroupchangerequests"] = HpcGroupChangeRequest.objects.filter(group=group)
            context["hpcprojectchangerequests"] = HpcProjectChangeRequest.objects.prefetch_related(
                "project__group", "project__delegate"
            ).filter(Q(project__group=group) | Q(project__delegate=context["object"]))
            context["hpcgroupdeleterequests"] = None
            context["hpcuserdeleterequests"] = None
            context["hpcprojectdeleterequests"] = None
            context["form_user_select"] = UserSelectForm(group=group)
            projects_available |= group.hpcprojects.exists()

        if is_project_manager:
            context["hpcprojectchangerequests"] = HpcProjectChangeRequest.objects.prefetch_related(
                "project__delegate"
            ).filter(project__delegate=context["object"])
            context["hpcprojectdeleterequests"] = None
            projects_available |= context["object"].hpcproject_delegate.exists()

        if is_project_manager or is_group_manager:
            context["form_project_select"] = ProjectSelectForm(user=context["object"])
            context["projects_available"] = projects_available

        return context


class HpcUserDetailView(HpcPermissionMixin, DetailView):
    """HPC user detail view."""

    model = HpcUser
    template_name = "usersec/hpcuser_detail.html"
    slug_field = "uuid"
    slug_url_kwarg = "hpcuser"
    permission_required = "usersec.view_hpcuser"


class HpcGroupDetailView(HpcPermissionMixin, DetailView):
    """HPC group detail view."""

    model = HpcGroup
    template_name = "usersec/hpcgroup_detail.html"
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroup"
    permission_required = "usersec.view_hpcgroup"


class HpcUserCreateRequestCreateView(HpcPermissionMixin, CreateView):
    """HPC user create request create view.

    Using HpcGroup object for permission checking,
    it is not the object to be created.
    """

    # Required for permission checks, usually the CreateView doesn't have the current object
    # available
    model = HpcGroup
    template_name = "usersec/hpcusercreaterequest_form.html"
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroup"
    # Check permission based on HpcGroup object
    permission_required = "usersec.create_hpcusercreaterequest"
    # Pass the form to the actual object we want to create
    form_class = HpcUserCreateRequestForm

    def get_permission_object(self):
        """Override to return the HpcGroup object.

        Parent returns None in case of CreateView.
        """
        return self.get_object()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.requester = self.request.user
        obj.editor = self.request.user
        obj.status = REQUEST_STATUS_ACTIVE
        obj.group = self.get_object()
        obj = obj.save_with_version()

        if not obj:
            messages.error(
                self.request, MSG_REQUEST_FAILURE.format(MSG_PART_SUBMIT, MSG_PART_USER_CREATION)
            )
            return HttpResponseRedirect(
                reverse("usersec:hpcgroup-details", kwargs={"hpcgroup": obj.group.uuid})
            )

        if settings.SEND_EMAIL:
            send_notification_admin_request(obj)

        messages.success(
            self.request, MSG_REQUEST_FAILURE.format(MSG_PART_SUBMITTED, MSG_PART_USER_CREATION)
        )
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcusercreaterequest-detail",
                kwargs={"hpcusercreaterequest": obj.uuid},
            )
        )


class HpcUserCreateRequestDetailView(HpcPermissionMixin, DetailView):
    """HPC user create request detail view."""

    model = HpcUserCreateRequest
    template_name = "usersec/hpcusercreaterequest_detail.html"
    slug_field = "uuid"
    slug_url_kwarg = "hpcusercreaterequest"
    permission_required = "usersec.view_hpcusercreaterequest"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context["is_decided"] = obj.is_decided()
        context["is_denied"] = obj.is_denied()
        context["is_retracted"] = obj.is_retracted()
        context["is_approved"] = obj.is_approved()
        context["is_active"] = obj.is_active()
        context["is_revision"] = obj.is_revision()
        context["is_revised"] = obj.is_revised()
        return context


class HpcUserCreateRequestUpdateView(HpcPermissionMixin, UpdateView):
    """HPC user create request update view."""

    template_name = "usersec/hpcusercreaterequest_form.html"
    model = HpcUserCreateRequest
    form_class = HpcUserCreateRequestForm
    slug_field = "uuid"
    slug_url_kwarg = "hpcusercreaterequest"
    permission_required = "usersec.manage_hpcusercreaterequest"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["update"] = True
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def get_success_url(self):
        return reverse(
            "usersec:hpcusercreaterequest-detail",
            kwargs={"hpcusercreaterequest": self.get_object().uuid},
        )

    def get_initial(self):
        initial = super().get_initial()
        initial["comment"] = ""
        return initial

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.editor = self.request.user
        status = obj.status

        if status == REQUEST_STATUS_REVISION:
            obj = obj.revised_with_version()

        else:
            obj = obj.save_with_version()

        if not obj:
            messages.error(
                self.request, MSG_REQUEST_FAILURE.format(MSG_PART_UPDATE, MSG_PART_USER_CREATION)
            )
            return HttpResponseRedirect(reverse("home"))

        if settings.SEND_EMAIL:
            send_notification_admin_request(obj)

        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_UPDATED, MSG_PART_USER_CREATION)
        )
        return HttpResponseRedirect(self.get_success_url())


class HpcUserCreateRequestRetractView(HpcPermissionMixin, DeleteView):
    """HPC user create request update view."""

    template_name_suffix = "_retract_confirm"
    model = HpcUserCreateRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcusercreaterequest"
    permission_required = "usersec.manage_hpcusercreaterequest"

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.comment = COMMENT_RETRACTED
        obj.editor = self.request.user
        obj.retract_with_version()

        # No email notification required
        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_RETRACTED, MSG_PART_USER_CREATION)
        )
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcusercreaterequest-detail",
                kwargs={"hpcusercreaterequest": obj.uuid},
            )
        )


class HpcUserCreateRequestReactivateView(HpcPermissionMixin, SingleObjectMixin, View):
    """HPC user create request update view."""

    model = HpcUserCreateRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcusercreaterequest"
    permission_required = "usersec.manage_hpcusercreaterequest"

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.status = REQUEST_STATUS_ACTIVE
        obj.comment = COMMENT_REACTIVATED
        obj.editor = self.request.user
        obj.save_with_version()

        if settings.SEND_EMAIL:
            send_notification_admin_request(obj)

        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_REACTIVATED, MSG_PART_USER_CREATION)
        )
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcusercreaterequest-detail",
                kwargs={"hpcusercreaterequest": obj.uuid},
            )
        )


class HpcGroupDeleteRequestCreateView(View):
    pass


class HpcGroupDeleteRequestDetailView(HpcPermissionMixin, DeleteView):
    pass


class HpcGroupDeleteRequestUpdateView(View):
    pass


class HpcGroupDeleteRequestRetractView(View):
    pass


class HpcGroupDeleteRequestReactivateView(View):
    pass


class HpcGroupChangeRequestCreateView(HpcPermissionMixin, CreateView):
    """HPC group change request create view.

    Using HpcGroup object for permission checking,
    it is not the object to be created.
    """

    # Required for permission checks, usually the CreateView doesn't have the current object
    # available
    model = HpcGroup
    template_name = "usersec/hpcgroupchangerequest_form.html"
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroup"
    # Check permission based on HpcGroup object
    permission_required = "usersec.create_hpcgroupchangerequest"
    # Pass the form to the actual object we want to create
    form_class = HpcGroupChangeRequestForm

    def get_permission_object(self):
        """Override to return the HpcGroup object.

        Parent returns None in case of CreateView.
        """
        return self.get_object()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user, "group": self.get_object()})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"group": self.get_object()})
        return context

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.requester = self.request.user
        obj.editor = self.request.user
        obj.status = REQUEST_STATUS_ACTIVE
        obj.group = self.get_object()
        obj = obj.save_with_version()

        if not obj:
            messages.error(
                self.request, MSG_REQUEST_FAILURE.format(MSG_PART_SUBMIT, MSG_PART_GROUP_UPDATE)
            )
            return HttpResponseRedirect(
                reverse("usersec:hpcgroup-detail", kwargs={"hpcgroup": obj.group.uuid})
            )

        if settings.SEND_EMAIL:
            send_notification_admin_request(obj)

        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_SUBMITTED, MSG_PART_GROUP_UPDATE)
        )
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcgroupchangerequest-detail",
                kwargs={"hpcgroupchangerequest": obj.uuid},
            )
        )


class HpcGroupChangeRequestDetailView(HpcPermissionMixin, DetailView):
    """HPC group change request detail view."""

    model = HpcGroupChangeRequest
    template_name = "usersec/hpcgroupchangerequest_detail.html"
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupchangerequest"
    permission_required = "usersec.view_hpcgroupchangerequest"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context["is_decided"] = obj.is_decided()
        context["is_denied"] = obj.is_denied()
        context["is_retracted"] = obj.is_retracted()
        context["is_approved"] = obj.is_approved()
        context["is_active"] = obj.is_active()
        context["is_revision"] = obj.is_revision()
        context["is_revised"] = obj.is_revised()
        return context


class HpcGroupChangeRequestUpdateView(HpcPermissionMixin, UpdateView):
    """HPC group change request update view."""

    template_name = "usersec/hpcgroupchangerequest_form.html"
    form_class = HpcGroupChangeRequestForm
    model = HpcGroupChangeRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupchangerequest"
    permission_required = "usersec.manage_hpcgroupchangerequest"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["update"] = True
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user, "group": self.get_object().group})
        return kwargs

    def get_success_url(self):
        return reverse(
            "usersec:hpcgroupchangerequest-detail",
            kwargs={"hpcgroupchangerequest": self.get_object().uuid},
        )

    def get_initial(self):
        initial = super().get_initial()
        initial["comment"] = ""
        return initial

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.editor = self.request.user
        status = obj.status

        if status == REQUEST_STATUS_REVISION:
            obj = obj.revised_with_version()

        else:
            obj = obj.save_with_version()

        if not obj:
            messages.error(
                self.request, MSG_REQUEST_FAILURE.format(MSG_PART_UPDATE, MSG_PART_GROUP_UPDATE)
            )
            return HttpResponseRedirect(reverse("home"))

        # No email notification required
        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_UPDATED, MSG_PART_GROUP_UPDATE)
        )
        return HttpResponseRedirect(self.get_success_url())


class HpcGroupChangeRequestRetractView(HpcPermissionMixin, DeleteView):
    """HPC group change request retract view."""

    template_name_suffix = "_retract_confirm"
    model = HpcGroupChangeRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupchangerequest"
    permission_required = "usersec.manage_hpcgroupchangerequest"

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.comment = COMMENT_RETRACTED
        obj.editor = self.request.user
        obj.retract_with_version()

        # No email notification required
        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_RETRACTED, MSG_PART_GROUP_UPDATE)
        )
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcgroupchangerequest-detail",
                kwargs={"hpcgroupchangerequest": obj.uuid},
            )
        )


class HpcGroupChangeRequestReactivateView(HpcPermissionMixin, SingleObjectMixin, View):
    """HPC group change request update view."""

    model = HpcGroupChangeRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupchangerequest"
    permission_required = "usersec.manage_hpcgroupchangerequest"

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.status = REQUEST_STATUS_ACTIVE
        obj.comment = COMMENT_REACTIVATED
        obj.editor = self.request.user
        obj.save_with_version()

        if settings.SEND_EMAIL:
            send_notification_admin_request(obj)

        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_REACTIVATED, MSG_PART_GROUP_UPDATE)
        )
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcgroupchangerequest-detail",
                kwargs={"hpcgroupchangerequest": obj.uuid},
            )
        )


class HpcUserDeleteRequestCreateView(View):
    pass


class HpcUserDeleteRequestDetailView(View):
    pass


class HpcUserDeleteRequestUpdateView(View):
    pass


class HpcUserDeleteRequestRetractView(View):
    pass


class HpcUserDeleteRequestReactivateView(View):
    pass


class HpcUserChangeRequestCreateView(HpcPermissionMixin, CreateView):
    """HPC user change request create view.

    Using HpcUser object for permission checking,
    it is not the object to be created.
    """

    # Required for permission checks, usually the CreateView doesn't have the current object
    # available
    model = HpcUser
    template_name = "usersec/hpcuserchangerequest_form.html"
    slug_field = "uuid"
    slug_url_kwarg = "hpcuser"
    # Check permission based on HpcUser object
    permission_required = "usersec.create_hpcuserchangerequest"
    # Pass the form to the actual object we want to create
    form_class = HpcUserChangeRequestForm

    def get_permission_object(self):
        """Override to return the HpcUser object.

        Parent returns None in case of CreateView.
        """
        return self.get_object()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"user": self.get_object()})
        return context

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.requester = self.request.user
        obj.editor = self.request.user
        obj.status = REQUEST_STATUS_ACTIVE
        obj.user = self.get_object()
        obj = obj.save_with_version()

        if not obj:
            messages.error(
                self.request, MSG_REQUEST_FAILURE.format(MSG_PART_SUBMIT, MSG_PART_USER_UPDATE)
            )
            return HttpResponseRedirect(reverse("home"))

        if settings.SEND_EMAIL:
            send_notification_admin_request(obj)

        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_SUBMITTED, MSG_PART_USER_UPDATE)
        )
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcuserchangerequest-detail",
                kwargs={"hpcuserchangerequest": obj.uuid},
            )
        )


class HpcUserChangeRequestDetailView(HpcPermissionMixin, DetailView):
    """HPC user change request detail view."""

    model = HpcUserChangeRequest
    template_name = "usersec/hpcuserchangerequest_detail.html"
    slug_field = "uuid"
    slug_url_kwarg = "hpcuserchangerequest"
    permission_required = "usersec.view_hpcuserchangerequest"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context["is_decided"] = obj.is_decided()
        context["is_denied"] = obj.is_denied()
        context["is_retracted"] = obj.is_retracted()
        context["is_approved"] = obj.is_approved()
        context["is_active"] = obj.is_active()
        context["is_revision"] = obj.is_revision()
        context["is_revised"] = obj.is_revised()
        return context


class HpcUserChangeRequestUpdateView(HpcPermissionMixin, UpdateView):
    """HPC user change request update view."""

    template_name = "usersec/hpcuserchangerequest_form.html"
    form_class = HpcUserChangeRequestForm
    model = HpcUserChangeRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcuserchangerequest"
    permission_required = "usersec.manage_hpcuserchangerequest"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["update"] = True
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def get_success_url(self):
        return reverse(
            "usersec:hpcuserchangerequest-detail",
            kwargs={"hpcuserchangerequest": self.get_object().uuid},
        )

    def get_initial(self):
        initial = super().get_initial()
        initial["comment"] = ""
        return initial

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.editor = self.request.user
        status = obj.status

        if status == REQUEST_STATUS_REVISION:
            obj = obj.revised_with_version()

        else:
            obj = obj.save_with_version()

        if not obj:
            messages.error(
                self.request, MSG_REQUEST_FAILURE.format(MSG_PART_UPDATE, MSG_PART_USER_UPDATE)
            )
            return HttpResponseRedirect(reverse("home"))

        # No email notification required
        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_UPDATED, MSG_PART_USER_UPDATE)
        )
        return HttpResponseRedirect(self.get_success_url())


class HpcUserChangeRequestRetractView(HpcPermissionMixin, DeleteView):
    """HPC user change request update view."""

    template_name_suffix = "_retract_confirm"
    model = HpcUserChangeRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcuserchangerequest"
    permission_required = "usersec.manage_hpcuserchangerequest"

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.comment = COMMENT_RETRACTED
        obj.editor = self.request.user
        obj.retract_with_version()

        # No email notification required
        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_RETRACTED, MSG_PART_USER_UPDATE)
        )
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcuserchangerequest-detail",
                kwargs={"hpcuserchangerequest": obj.uuid},
            )
        )


class HpcUserChangeRequestReactivateView(HpcPermissionMixin, SingleObjectMixin, View):
    """HPC user change request update view."""

    model = HpcUserChangeRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcuserchangerequest"
    permission_required = "usersec.manage_hpcuserchangerequest"

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.status = REQUEST_STATUS_ACTIVE
        obj.comment = COMMENT_REACTIVATED
        obj.editor = self.request.user
        obj.save_with_version()

        if settings.SEND_EMAIL:
            send_notification_admin_request(obj)

        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_REACTIVATED, MSG_PART_USER_UPDATE)
        )
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcuserchangerequest-detail",
                kwargs={"hpcuserchangerequest": obj.uuid},
            )
        )


class HpcProjectDetailView(HpcPermissionMixin, DetailView):
    """HPC project detail view."""

    model = HpcProject
    template_name = "usersec/hpcproject_detail.html"
    slug_field = "uuid"
    slug_url_kwarg = "hpcproject"
    permission_required = "usersec.view_hpcproject"


class HpcProjectCreateRequestCreateView(HpcPermissionMixin, CreateView):
    """HPC project create request create view.

    Using HpcGroup object for permission checking,
    it is not the object to be created.
    """

    # Required for permission checks, usually the CreateView doesn't have the current object
    # available
    model = HpcGroup
    template_name = "usersec/hpcprojectcreaterequest_form.html"
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroup"
    # Check permission based on HpcGroup object
    permission_required = "usersec.create_hpcprojectcreaterequest"
    # Pass the form to the actual object we want to create
    form_class = HpcProjectCreateRequestForm

    def get_permission_object(self):
        """Override to return the HpcGroup object.

        Parent returns None in case of CreateView.
        """
        return self.get_object()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user, "group": self.get_object()})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"group": self.get_object()})
        return context

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.requester = self.request.user
        obj.editor = self.request.user
        obj.status = REQUEST_STATUS_ACTIVE
        obj.group = self.get_object()
        obj = obj.save_with_version()

        # Adding members possible only with saved object
        obj.members.set(form.cleaned_data["members"])
        obj.version_history.last().members.set(form.cleaned_data["members"])

        if not obj:
            messages.error(self.request, "Couldn't create project request.")
            return HttpResponseRedirect(
                reverse(
                    "usersec:hpcprojectchangerequest-create", kwargs={"hpcproject": obj.group.uuid}
                )
            )

        if settings.SEND_EMAIL:
            send_notification_admin_request(obj)
            send_notification_manager_project_request(obj)

        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_SUBMITTED, MSG_PART_PROJECT_CREATION)
        )
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcprojectcreaterequest-detail",
                kwargs={"hpcprojectcreaterequest": obj.uuid},
            )
        )


class HpcProjectCreateRequestDetailView(HpcPermissionMixin, DetailView):
    """HPC project create request detail view."""

    model = HpcProjectCreateRequest
    template_name = "usersec/hpcprojectcreaterequest_detail.html"
    slug_field = "uuid"
    slug_url_kwarg = "hpcprojectcreaterequest"
    permission_required = "usersec.view_hpcprojectcreaterequest"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context["is_decided"] = obj.is_decided()
        context["is_denied"] = obj.is_denied()
        context["is_retracted"] = obj.is_retracted()
        context["is_approved"] = obj.is_approved()
        context["is_active"] = obj.is_active()
        context["is_revision"] = obj.is_revision()
        context["is_revised"] = obj.is_revised()
        return context


class HpcProjectCreateRequestUpdateView(HpcPermissionMixin, UpdateView):
    """HPC project create request update view."""

    template_name = "usersec/hpcprojectcreaterequest_form.html"
    form_class = HpcProjectCreateRequestForm
    model = HpcProjectCreateRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcprojectcreaterequest"
    permission_required = "usersec.manage_hpcprojectcreaterequest"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["update"] = True
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def get_success_url(self):
        return reverse(
            "usersec:hpcprojectcreaterequest-detail",
            kwargs={"hpcprojectcreaterequest": self.get_object().uuid},
        )

    def get_initial(self):
        initial = super().get_initial()
        initial["comment"] = ""
        return initial

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.editor = self.request.user
        status = obj.status

        if status == REQUEST_STATUS_REVISION:
            obj = obj.revised_with_version()

        else:
            obj = obj.save_with_version()

        if not obj:
            messages.error(
                self.request, MSG_REQUEST_FAILURE.format(MSG_PART_UPDATE, MSG_PART_PROJECT_CREATION)
            )
            return HttpResponseRedirect(reverse("home"))

        obj.members.set(form.cleaned_data["members"])
        obj.version_history.last().members.set(form.cleaned_data["members"])

        # No email notification required
        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_UPDATED, MSG_PART_PROJECT_CREATION)
        )
        return HttpResponseRedirect(self.get_success_url())


class HpcProjectCreateRequestRetractView(HpcPermissionMixin, DeleteView):
    """HPC project create request update view."""

    template_name_suffix = "_retract_confirm"
    model = HpcProjectCreateRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcprojectcreaterequest"
    permission_required = "usersec.manage_hpcprojectcreaterequest"

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.comment = COMMENT_RETRACTED
        obj.editor = self.request.user
        obj.retract_with_version()

        # No email notification required
        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_RETRACTED, MSG_PART_PROJECT_CREATION)
        )

        return HttpResponseRedirect(
            reverse(
                "usersec:hpcprojectcreaterequest-detail",
                kwargs={"hpcprojectcreaterequest": obj.uuid},
            )
        )


class HpcProjectCreateRequestReactivateView(HpcPermissionMixin, SingleObjectMixin, View):
    """HPC project create request update view."""

    model = HpcProjectCreateRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcprojectcreaterequest"
    permission_required = "usersec.manage_hpcprojectcreaterequest"

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.status = REQUEST_STATUS_ACTIVE
        obj.comment = COMMENT_REACTIVATED
        obj.editor = self.request.user
        obj.save_with_version()

        if settings.SEND_EMAIL:
            send_notification_admin_request(obj)

        messages.success(
            self.request,
            MSG_REQUEST_SUCCESS.format(MSG_PART_REACTIVATED, MSG_PART_PROJECT_CREATION),
        )
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcprojectcreaterequest-detail",
                kwargs={"hpcprojectcreaterequest": obj.uuid},
            )
        )


class HpcProjectDeleteRequestCreateView(View):
    pass


class HpcProjectDeleteRequestDetailView(View):
    pass


class HpcProjectDeleteRequestUpdateView(View):
    pass


class HpcProjectDeleteRequestRetractView(View):
    pass


class HpcProjectDeleteRequestReactivateView(View):
    pass


class HpcProjectChangeRequestCreateView(HpcPermissionMixin, CreateView):
    """HPC project create request create view.

    Using HpcProject object for permission checking,
    it is not the object to be created.
    """

    # Required for permission checks, usually the CreateView doesn't have the current object
    # available
    model = HpcProject
    template_name = "usersec/hpcprojectchangerequest_form.html"
    slug_field = "uuid"
    slug_url_kwarg = "hpcproject"
    # Check permission based on HpcProject object
    permission_required = "usersec.create_hpcprojectchangerequest"
    # Pass the form to the actual object we want to create
    form_class = HpcProjectChangeRequestForm

    def get_permission_object(self):
        """Override to return the HpcGroup object.

        Parent returns None in case of CreateView.
        """
        return self.get_object()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user, "project": self.get_object()})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"project": self.get_object()})
        return context

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.requester = self.request.user
        obj.editor = self.request.user
        obj.status = REQUEST_STATUS_ACTIVE
        obj.project = self.get_object()
        obj = obj.save_with_version()

        # Adding members possible only with saved object
        obj.members.set(form.cleaned_data["members"])
        obj.version_history.last().members.set(form.cleaned_data["members"])

        if not obj:
            messages.error(
                self.request, MSG_REQUEST_FAILURE.format(MSG_PART_SUBMIT, MSG_PART_PROJECT_UPDATE)
            )
            return HttpResponseRedirect(
                reverse("usersec:hpcprojectchangerequest-create", kwargs={"hpcproject": obj.uuid})
            )

        if settings.SEND_EMAIL:
            send_notification_admin_request(obj)

        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_SUBMITTED, MSG_PART_PROJECT_UPDATE)
        )
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcprojectchangerequest-detail",
                kwargs={"hpcprojectchangerequest": obj.uuid},
            )
        )


class HpcProjectChangeRequestDetailView(HpcPermissionMixin, DetailView):
    """HPC project change request detail view."""

    model = HpcProjectChangeRequest
    template_name = "usersec/hpcprojectchangerequest_detail.html"
    slug_field = "uuid"
    slug_url_kwarg = "hpcprojectchangerequest"
    permission_required = "usersec.view_hpcprojectchangerequest"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context["is_decided"] = obj.is_decided()
        context["is_denied"] = obj.is_denied()
        context["is_retracted"] = obj.is_retracted()
        context["is_approved"] = obj.is_approved()
        context["is_active"] = obj.is_active()
        context["is_revision"] = obj.is_revision()
        context["is_revised"] = obj.is_revised()
        return context


class HpcProjectChangeRequestUpdateView(HpcPermissionMixin, UpdateView):
    """HPC project change request update view."""

    template_name = "usersec/hpcprojectchangerequest_form.html"
    form_class = HpcProjectChangeRequestForm
    model = HpcProjectChangeRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcprojectchangerequest"
    permission_required = "usersec.manage_hpcprojectchangerequest"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["update"] = True
        context["project"] = self.get_object().project
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user, "project": self.get_object().project})
        return kwargs

    def get_success_url(self):
        return reverse(
            "usersec:hpcprojectchangerequest-detail",
            kwargs={"hpcprojectchangerequest": self.get_object().uuid},
        )

    def get_initial(self):
        initial = super().get_initial()
        initial["comment"] = ""
        return initial

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.editor = self.request.user

        if obj.status == REQUEST_STATUS_REVISION:
            obj = obj.revised_with_version()

        else:
            obj = obj.save_with_version()

        if not obj:
            messages.error(
                self.request, MSG_REQUEST_FAILURE.format(MSG_PART_UPDATE, MSG_PART_PROJECT_UPDATE)
            )
            return HttpResponseRedirect(reverse("home"))

        # No email notification required
        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_UPDATED, MSG_PART_PROJECT_UPDATE)
        )
        return HttpResponseRedirect(self.get_success_url())


class HpcProjectChangeRequestRetractView(HpcPermissionMixin, DeleteView):
    """HPC project change request retract view."""

    template_name_suffix = "_retract_confirm"
    model = HpcProjectChangeRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcprojectchangerequest"
    permission_required = "usersec.manage_hpcprojectchangerequest"

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.comment = COMMENT_RETRACTED
        obj.editor = self.request.user
        obj.retract_with_version()

        # No email notification required
        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_RETRACTED, MSG_PART_PROJECT_UPDATE)
        )
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcprojectchangerequest-detail",
                kwargs={"hpcprojectchangerequest": obj.uuid},
            )
        )


class HpcProjectChangeRequestReactivateView(HpcPermissionMixin, SingleObjectMixin, View):
    """HPC project change request update view."""

    model = HpcProjectChangeRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcprojectchangerequest"
    permission_required = "usersec.manage_hpcprojectchangerequest"

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.status = REQUEST_STATUS_ACTIVE
        obj.comment = COMMENT_REACTIVATED
        obj.editor = self.request.user
        obj.save_with_version()

        if settings.SEND_EMAIL:
            send_notification_admin_request(obj)

        messages.success(
            self.request, MSG_REQUEST_SUCCESS.format(MSG_PART_REACTIVATED, MSG_PART_PROJECT_UPDATE)
        )
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcprojectchangerequest-detail",
                kwargs={"hpcprojectchangerequest": obj.uuid},
            )
        )


class HpcGroupInvitationDetailView(HpcPermissionMixin, DetailView):
    """HPC group invitation detail view."""

    template_name = "usersec/hpcgroupinvitation_detail.html"
    model = HpcGroupInvitation
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupinvitation"
    permission_required = "usersec.manage_hpcgroupinvitation"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["terms_list"] = TermsAndConditions.objects.filter(
            audience=TERMS_AUDIENCE_USER, date_published__isnull=False
        )
        return context


class HpcGroupInvitationAcceptView(HpcPermissionMixin, SingleObjectMixin, View):
    """HPC group invitation accept view."""

    model = HpcGroupInvitation
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupinvitation"
    permission_required = "usersec.manage_hpcgroupinvitation"

    @transaction.atomic
    def get(self, request, *args, **kwargs):
        obj = self.get_object()

        if self.request.user.is_superuser:
            messages.error(request, MSG_INVITATION_SUPERUSER)
            return HttpResponseRedirect(
                reverse(
                    "usersec:hpcgroupinvitation-detail",
                    kwargs={"hpcgroupinvitation": obj.uuid},
                )
            )

        obj.status = INVITATION_STATUS_ACCEPTED
        obj.save_with_version()

        try:
            from adminsec.views import django_to_hpc_username

            username = django_to_hpc_username(obj.username)

            hpcuser = HpcUser.objects.create_with_version(
                user=request.user,
                primary_group=obj.hpcusercreaterequest.group,
                resources_requested=obj.hpcusercreaterequest.resources_requested,
                creator=obj.hpcusercreaterequest.editor,
                username=username,
                status=OBJECT_STATUS_ACTIVE,
                expiration=obj.hpcusercreaterequest.expiration,
                home_directory=DEFAULT_HOME_DIRECTORY.format(username=username),
            )

        except Exception as e:
            messages.error(request, MSG_INVITATION_GROUP_USER_CREATE_FAILURE.format(e))
            return HttpResponseRedirect(
                reverse(
                    "usersec:hpcgroupinvitation-detail",
                    kwargs={"hpcgroupinvitation": obj.uuid},
                )
            )

        if settings.SEND_EMAIL:
            send_notification_manager_user_decided_invitation(obj)
            send_notification_user_welcome_mail(hpcuser)

        messages.success(request, MSG_INVITATION_GROUP_USER_CREATE_SUCCESS)
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcuser-overview",
                kwargs={"hpcuser": hpcuser.uuid},
            )
        )


class HpcGroupInvitationRejectView(HpcPermissionMixin, DeleteView):
    """HPC group invitation reject view."""

    template_name_suffix = "_reject_confirm"
    model = HpcGroupInvitation
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupinvitation"
    permission_required = "usersec.manage_hpcgroupinvitation"

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.status = INVITATION_STATUS_REJECTED
        obj.save_with_version()

        if settings.SEND_EMAIL:
            send_notification_manager_user_decided_invitation(obj)

        messages.success(request, MSG_INVITATION_REJECTED_SUCCESS)
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcgroupinvitation-detail",
                kwargs={"hpcgroupinvitation": obj.uuid},
            )
        )


class HpcProjectInvitationAcceptView(HpcPermissionMixin, SingleObjectMixin, View):
    """HPC project invitation accept view."""

    model = HpcProjectInvitation
    slug_field = "uuid"
    slug_url_kwarg = "hpcprojectinvitation"
    permission_required = "usersec.manage_hpcprojectinvitation"

    def get(self, request, *args, **kwargs):
        obj = self.get_object()

        if request.user.is_superuser:
            messages.error(
                request,
                MSG_INVITATION_SUPERUSER,
            )
            return HttpResponseRedirect(reverse("home"))

        obj.status = INVITATION_STATUS_ACCEPTED
        obj.save_with_version()

        project = obj.project

        try:
            project.save_with_version()
            project.members.add(obj.user)
            project.version_history.last().members.add(obj.user)

        except Exception as e:
            messages.error(request, MSG_INVITATION_PROJECT_USER_ADD_FAILURE.format(e))
            return HttpResponseRedirect(
                reverse(
                    "usersec:hpcuser-overview",
                    kwargs={"hpcuser": request.user.hpcuser_user.first().uuid},
                )
            )

        if settings.SEND_EMAIL:
            send_notification_manager_user_decided_invitation(obj)

        messages.success(request, MSG_INVITATION_PROJECT_USER_ADD_SUCCESS)
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcuser-overview",
                kwargs={"hpcuser": request.user.hpcuser_user.first().uuid},
            )
        )


class HpcProjectInvitationRejectView(HpcPermissionMixin, DeleteView):
    """HPC project invitation reject view."""

    template_name_suffix = "_reject_confirm"
    model = HpcProjectInvitation
    slug_field = "uuid"
    slug_url_kwarg = "hpcprojectinvitation"
    permission_required = "usersec.manage_hpcprojectinvitation"

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.status = INVITATION_STATUS_REJECTED
        obj.save_with_version()

        if settings.SEND_EMAIL:
            send_notification_manager_user_decided_invitation(obj)

        messages.success(self.request, MSG_INVITATION_REJECTED_SUCCESS)
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcuser-overview",
                kwargs={"hpcuser": obj.user.uuid},
            )
        )


def get_terms_and_conditions(request):
    hpcuser = HpcUser.objects.filter(user=request.user)
    audience = [TERMS_AUDIENCE_ALL]

    if hpcuser.exists():
        audience.append(TERMS_AUDIENCE_PI if hpcuser.first().is_pi else TERMS_AUDIENCE_USER)

    return TermsAndConditions.objects.filter(audience__in=audience, date_published__isnull=False)


class TermsAndConditionsView(ListView):
    """View for consenting to terms and conditions."""

    model = TermsAndConditions
    template_name = "usersec/terms.html"

    def get_queryset(self):
        return get_terms_and_conditions(self.request)

    def post(self, request, *args, **kwargs):
        request.user.consented_to_terms = True
        request.user.save()

        messages.success(self.request, MSG_TERMS_CONSENT)
        return HttpResponseRedirect(reverse("home"))
