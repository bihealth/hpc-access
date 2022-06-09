import rules
from django.conf import settings

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    UpdateView,
)
from django.views.generic.detail import SingleObjectMixin
from rules.contrib.views import PermissionRequiredMixin

from adminsec.email import (
    send_notification_request_status_changed,
    send_notification_user_decided_invitation,
    send_notification_object_created,
)
from usersec.forms import (
    HpcGroupCreateRequestForm,
    HpcUserCreateRequestForm,
    HpcProjectCreateRequestForm,
    HpcGroupChangeRequestForm,
    HpcUserChangeRequestForm,
    UserSelectForm,
    HpcProjectChangeRequestForm,
    ProjectSelectForm,
)
from usersec.models import (
    HpcGroupCreateRequest,
    REQUEST_STATUS_ACTIVE,
    HpcUser,
    HpcGroup,
    HpcUserCreateRequest,
    REQUEST_STATUS_REVISION,
    HpcProject,
    HpcProjectCreateRequest,
    HpcGroupInvitation,
    INVITATION_STATUS_ACCEPTED,
    OBJECT_STATUS_ACTIVE,
    INVITATION_STATUS_REJECTED,
    HpcProjectInvitation,
    HpcGroupChangeRequest,
    HpcUserChangeRequest,
    HpcProjectChangeRequest,
)

MSG_NO_AUTH = "User not authorized for requested action"
MSG_NO_AUTH_LOGIN = MSG_NO_AUTH + ", please log in"


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
        if request.user.is_hpcadmin:
            return redirect(reverse("adminsec:overview"))

        elif rules.test_rule("usersec.is_cluster_user", request.user):
            return redirect(
                reverse(
                    "usersec:hpcuser-overview",
                    kwargs={"hpcuser": request.user.hpcuser_user.first().uuid},
                )
            )

        elif rules.test_rule("usersec.has_pending_group_request", request.user):
            return redirect(
                reverse(
                    "usersec:hpcgroupcreaterequest-detail",
                    kwargs={
                        "hpcgroupcreaterequest": request.user.hpcgroupcreaterequest_requester.first().uuid
                    },
                )
            )

        elif rules.test_rule("usersec.has_group_invitation", request.user):
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

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.requester = self.request.user
        obj.editor = self.request.user
        obj.status = REQUEST_STATUS_ACTIVE
        obj = obj.save_with_version()

        if not obj:
            messages.error(self.request, "Couldn't create group request.")
            return HttpResponseRedirect(reverse("usersec:orphan-user"))

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            send_notification_request_status_changed(
                recipient_list=[obj.requester.email] + get_admin_emails(),
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "Group request submitted.")
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
            messages.error(self.request, "Couldn't update group request.")
            return HttpResponseRedirect(reverse("usersec:orphan-user"))

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            emails = [obj.requester.email]

            if status == REQUEST_STATUS_REVISION:
                emails += get_admin_emails()

            send_notification_request_status_changed(
                recipient_list=emails,
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "Group request updated.")
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
        obj.comment = "Request retracted"
        obj.editor = self.request.user
        obj.retract_with_version()
        messages.success(self.request, "Request successfully retracted.")

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            send_notification_request_status_changed(
                recipient_list=[obj.requester.email] + get_admin_emails(),
                obj=obj,
                request=self.request,
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
        obj.comment = "Request reactivated"
        obj.editor = self.request.user
        obj.save_with_version()

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            send_notification_request_status_changed(
                recipient_list=[obj.requester.email] + get_admin_emails(),
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "Request successfully re-activated.")
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

    # Required for permission checks, usually the CreateView doesn't have the current object available
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
            messages.error(self.request, "Couldn't create user request.")
            return HttpResponseRedirect(
                reverse("usersec:hpcgroup-details", kwargs={"hpcgroup": obj.group.uuid})
            )

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            send_notification_request_status_changed(
                recipient_list=obj.group.get_manager_emails() + get_admin_emails(),
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "User request submitted.")
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
            messages.error(self.request, "Couldn't update user request.")
            return HttpResponseRedirect(reverse("home"))

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            emails = obj.group.get_manager_emails()

            if status == REQUEST_STATUS_REVISION:
                emails += get_admin_emails()

            send_notification_request_status_changed(
                recipient_list=emails,
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "User request updated.")
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
        obj.comment = "Request retracted"
        obj.editor = self.request.user
        obj.retract_with_version()

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            send_notification_request_status_changed(
                recipient_list=obj.group.get_manager_emails() + get_admin_emails(),
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "Request successfully retracted.")
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
        obj.comment = "Request reactivated"
        obj.editor = self.request.user
        obj.save_with_version()

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            send_notification_request_status_changed(
                recipient_list=obj.group.get_manager_emails() + get_admin_emails(),
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "Request successfully re-activated.")
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

    # Required for permission checks, usually the CreateView doesn't have the current object available
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
            messages.error(self.request, "Couldn't create group change request.")
            return HttpResponseRedirect(
                reverse("usersec:hpcgroup-detail", kwargs={"hpcgroup": obj.group.uuid})
            )

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            send_notification_request_status_changed(
                recipient_list=obj.group.get_manager_emails() + get_admin_emails(),
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "Project request submitted.")
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
            messages.error(self.request, "Couldn't update group change request.")
            return HttpResponseRedirect(reverse("home"))

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            emails = obj.group.get_manager_emails()

            if status == REQUEST_STATUS_REVISION:
                emails += get_admin_emails()

            send_notification_request_status_changed(
                recipient_list=emails,
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "Group change request updated.")
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
        obj.comment = "Request retracted"
        obj.editor = self.request.user
        obj.retract_with_version()

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            send_notification_request_status_changed(
                recipient_list=obj.group.get_manager_emails() + get_admin_emails(),
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "Request successfully retracted.")
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
        obj.comment = "Request reactivated"
        obj.editor = self.request.user
        obj.save_with_version()

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            send_notification_request_status_changed(
                recipient_list=obj.group.get_manager_emails() + get_admin_emails(),
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "Request successfully re-activated.")
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

    # Required for permission checks, usually the CreateView doesn't have the current object available
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
            messages.error(self.request, "Couldn't create user change request.")
            return HttpResponseRedirect(reverse("home"))

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            send_notification_request_status_changed(
                recipient_list=obj.user.primary_group.get_manager_emails() + get_admin_emails(),
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "User change request submitted.")
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
            messages.error(self.request, "Couldn't update user change request.")
            return HttpResponseRedirect(reverse("home"))

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            emails = obj.user.primary_group.get_manager_emails()

            if status == REQUEST_STATUS_REVISION:
                emails += get_admin_emails()

            send_notification_request_status_changed(
                recipient_list=emails,
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "User change request updated.")
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
        obj.comment = "Request retracted"
        obj.editor = self.request.user
        obj.retract_with_version()

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            send_notification_request_status_changed(
                recipient_list=obj.user.primary_group.get_manager_emails() + get_admin_emails(),
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "Request successfully retracted.")
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
        obj.comment = "Request reactivated"
        obj.editor = self.request.user
        obj.save_with_version()

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            send_notification_request_status_changed(
                recipient_list=obj.user.primary_group.get_manager_emails() + get_admin_emails(),
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "Request successfully re-activated.")
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

    # Required for permission checks, usually the CreateView doesn't have the current object available
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
            from adminsec.views import get_admin_emails

            send_notification_request_status_changed(
                recipient_list=obj.group.get_manager_emails() + get_admin_emails(),
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "Project request submitted.")
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
            messages.error(self.request, "Couldn't update project request.")
            return HttpResponseRedirect(reverse("home"))

        obj.members.set(form.cleaned_data["members"])
        obj.version_history.last().members.set(form.cleaned_data["members"])

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            emails = obj.group.get_manager_emails()

            if status == REQUEST_STATUS_REVISION:
                emails += get_admin_emails()

            send_notification_request_status_changed(
                recipient_list=emails,
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "Project request updated.")
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
        obj.comment = "Request retracted"
        obj.editor = self.request.user
        obj.retract_with_version()
        messages.success(self.request, "Request successfully retracted.")

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            send_notification_request_status_changed(
                recipient_list=obj.group.get_manager_emails() + get_admin_emails(),
                obj=obj,
                request=self.request,
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
        obj.comment = "Request reactivated"
        obj.editor = self.request.user
        obj.save_with_version()

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            send_notification_request_status_changed(
                recipient_list=obj.group.get_manager_emails() + get_admin_emails(),
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "Request successfully re-activated.")
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

    # Required for permission checks, usually the CreateView doesn't have the current object available
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
            messages.error(self.request, "Couldn't create project change request.")
            return HttpResponseRedirect(
                reverse("usersec:hpcprojectchangerequest-create", kwargs={"hpcproject": obj.uuid})
            )

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            send_notification_request_status_changed(
                recipient_list=obj.project.get_manager_emails() + get_admin_emails(),
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "Project change request submitted.")
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
        status = obj.status

        if obj.status == REQUEST_STATUS_REVISION:
            obj = obj.revised_with_version()

        else:
            obj = obj.save_with_version()

        if not obj:
            messages.error(self.request, "Couldn't update project change request.")
            return HttpResponseRedirect(reverse("home"))

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            emails = obj.project.get_manager_emails()

            if status == REQUEST_STATUS_REVISION:
                emails += get_admin_emails()

            send_notification_request_status_changed(
                recipient_list=emails,
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "Project change request updated.")
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
        obj.comment = "Request retracted"
        obj.editor = self.request.user
        obj.retract_with_version()

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            send_notification_request_status_changed(
                recipient_list=obj.project.get_manager_emails() + get_admin_emails(),
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "Request successfully retracted.")
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
        obj.comment = "Request reactivated"
        obj.editor = self.request.user
        obj.save_with_version()

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            send_notification_request_status_changed(
                recipient_list=obj.project.get_manager_emails() + get_admin_emails(),
                obj=obj,
                request=self.request,
            )

        messages.success(self.request, "Request successfully re-activated.")
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


class HpcGroupInvitationAcceptView(HpcPermissionMixin, SingleObjectMixin, View):
    """HPC group invitation accept view."""

    model = HpcGroupInvitation
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupinvitation"
    permission_required = "usersec.manage_hpcgroupinvitation"

    def get(self, request, *args, **kwargs):
        obj = self.get_object()

        if self.request.user.is_superuser:
            messages.error(
                request,
                "Superuser is not allowed to accept invitations. This would lead to inconsistencies.",
            )
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

            hpcuser = HpcUser.objects.create_with_version(
                user=request.user,
                primary_group=obj.hpcusercreaterequest.group,
                resources_requested=obj.hpcusercreaterequest.resources_requested,
                creator=obj.hpcusercreaterequest.editor,
                username=django_to_hpc_username(obj.username),
                status=OBJECT_STATUS_ACTIVE,
                expiration=obj.hpcusercreaterequest.expiration,
            )

        except Exception as e:
            messages.error(request, "Could not create user: {}".format(e))
            return HttpResponseRedirect(
                reverse(
                    "usersec:hpcgroupinvitation-detail",
                    kwargs={"hpcgroupinvitation": obj.uuid},
                )
            )

        if settings.SEND_EMAIL:
            from adminsec.views import get_admin_emails

            send_notification_user_decided_invitation(
                invitation=obj,
                request=self.request,
            )
            send_notification_object_created(
                recipient_list=hpcuser.primary_group.get_manager_emails() + get_admin_emails(),
                obj=hpcuser,
                request=self.request,
            )

        messages.success(request, "Invitation successfully accepted and user created.")
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
            send_notification_user_decided_invitation(
                invitation=obj,
                request=self.request,
            )

        messages.success(request, "Invitation successfully rejected.")
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
                "Superuser is not allowed to accept invitations. This would lead to inconsistencies.",
            )
            return HttpResponseRedirect(reverse("home"))

        obj.status = INVITATION_STATUS_ACCEPTED
        obj.save_with_version()

        project = obj.project

        try:
            request_obj = obj.hpcprojectcreaterequest or obj.hpcprojectchangerequest
            if request_obj.delegate:
                if request.user.hpcuser_user.filter(id=request_obj.delegate.id).exists():
                    project.delegate = request_obj.delegate

            project.save_with_version()
            project.members.add(obj.user)
            project.version_history.last().members.add(obj.user)

        except Exception as e:
            messages.error(request, "Could not add user to project: {}".format(e))
            return HttpResponseRedirect(
                reverse(
                    "usersec:hpcuser-overview",
                    kwargs={"hpcuser": request.user.hpcuser_user.first().uuid},
                )
            )

        if settings.SEND_EMAIL:
            send_notification_user_decided_invitation(
                invitation=obj,
                request=self.request,
            )

        messages.success(request, "Successfully joined the project.")
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
            send_notification_user_decided_invitation(
                invitation=obj,
                request=self.request,
            )

        messages.success(self.request, "Invitation successfully rejected.")
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcuser-overview",
                kwargs={"hpcuser": obj.user.uuid},
            )
        )
