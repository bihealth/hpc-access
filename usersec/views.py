import rules

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
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

from usersec.forms import HpcGroupCreateRequestForm, HpcUserCreateRequestForm
from usersec.models import (
    HpcGroupCreateRequest,
    REQUEST_STATUS_ACTIVE,
    HpcUser,
    HpcGroup,
    HpcUserCreateRequest,
    REQUEST_STATUS_REVISION,
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

        elif rules.test_rule("usersec.is_cluster_user", request.user):  # noqa: E1101
            return redirect(
                reverse(
                    "usersec:hpcuser-overview",
                    kwargs={"hpcuser": request.user.hpcuser_user.first().uuid},
                )
            )

        elif rules.test_rule("usersec.has_pending_group_request", request.user):  # noqa: E1101
            return redirect(
                reverse(
                    "usersec:hpcgroupcreaterequest-detail",
                    kwargs={
                        "hpcgroupcreaterequest": request.user.hpcgroupcreaterequest_requester.first().uuid
                    },
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

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.requester = self.request.user
        obj.editor = self.request.user
        obj.status = REQUEST_STATUS_ACTIVE
        obj = obj.save_with_version()

        if not obj:
            messages.error(self.request, "Couldn't create group request.")
            return HttpResponseRedirect(reverse("usersec:orphan-user"))

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
        context["comment_history"] = obj.get_comment_history()
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
    fields = [
        "resources_requested",
        "description",
        "expiration",
        "comment",
    ]
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupcreaterequest"
    permission_required = "usersec.manage_hpcgroupcreaterequest"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context["update"] = True
        context["comment_history"] = obj.get_comment_history()
        return context

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

        if obj.status == REQUEST_STATUS_REVISION:
            obj = obj.revised_with_version()

        else:
            obj = obj.save_with_version()

        if not obj:
            messages.error(self.request, "Couldn't update group request.")
            return HttpResponseRedirect(reverse("usersec:orphan-user"))

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
        is_manager = rules.test_rule(
            "usersec.is_group_manager", self.request.user, group
        )  # noqa: E1101
        context["manager"] = is_manager

        if is_manager:
            context["hpcusercreaterequests"] = HpcUserCreateRequest.objects.filter(group=group)

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

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.requester = self.request.user
        obj.editor = self.request.user
        obj.status = REQUEST_STATUS_ACTIVE
        obj.group = self.get_object()
        obj = obj.save_with_version()

        if not obj:
            messages.error(self.request, "Couldn't create group request.")
            return HttpResponseRedirect(
                reverse("usersec:hpcgroup-detail", kwargs={"hpcgroup": obj.group.uuid})
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
        context["comment_history"] = obj.get_comment_history()
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
    fields = [
        "resources_requested",
        "email",
        "expiration",
        "comment",
    ]
    slug_field = "uuid"
    slug_url_kwarg = "hpcusercreaterequest"
    permission_required = "usersec.manage_hpcusercreaterequest"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context["update"] = True
        context["comment_history"] = obj.get_comment_history()
        return context

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

        if obj.status == REQUEST_STATUS_REVISION:
            obj = obj.revised_with_version()

        else:
            obj = obj.save_with_version()

        if not obj:
            messages.error(self.request, "Couldn't update user request.")
            return HttpResponseRedirect(reverse("home"))

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
        messages.success(self.request, "Request successfully re-activated.")
        return HttpResponseRedirect(
            reverse(
                "usersec:hpcusercreaterequest-detail",
                kwargs={"hpcusercreaterequest": obj.uuid},
            )
        )


class HpcGroupDeleteRequestCreateView(View):
    pass


class HpcGroupDeleteRequestDetailView(View):
    pass


class HpcGroupDeleteRequestUpdateView(View):
    pass


class HpcGroupDeleteRequestRetractView(View):
    pass


class HpcGroupDeleteRequestReactivateView(View):
    pass


class HpcGroupChangeRequestCreateView(View):
    pass


class HpcGroupChangeRequestDetailView(View):
    pass


class HpcGroupChangeRequestUpdateView(View):
    pass


class HpcGroupChangeRequestRetractView(View):
    pass


class HpcGroupChangeRequestReactivateView(View):
    pass


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


class HpcUserChangeRequestCreateView(View):
    pass


class HpcUserChangeRequestDetailView(View):
    pass


class HpcUserChangeRequestUpdateView(View):
    pass


class HpcUserChangeRequestRetractView(View):
    pass


class HpcUserChangeRequestReactivateView(View):
    pass
