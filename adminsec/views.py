import unicodedata
from datetime import timedelta

from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import (
    DetailView,
    UpdateView,
    DeleteView,
    TemplateView,
)

from usersec.forms import HpcGroupCreateRequestForm
from usersec.models import (
    HpcGroupCreateRequest,
    HpcGroup,
    HpcUser,
    OBJECT_STATUS_ACTIVE,
)
from usersec.views import HpcPermissionMixin


DOMAIN_MAPPING = {
    "CHARITE": "c",
    "MDC-BERLIN": "m",
}
AG_PREFIX = "ag_"
LDAP_USERNAME_SEPARATOR = "@"
HPC_USERNAME_SEPARATOR = "_"


def generate_hpc_username(username):
    fail_string = ""
    data = username.split(LDAP_USERNAME_SEPARATOR)

    if not len(data) == 2:
        return fail_string

    username, domain = data
    ending = DOMAIN_MAPPING.get(domain)

    if not ending:
        return fail_string

    return f"{username}{HPC_USERNAME_SEPARATOR}{ending}"


def convert_to_posix(name):
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")


def generate_hpc_groupname(name):
    return f"{AG_PREFIX}{convert_to_posix(name).lower()}"


class AdminView(HpcPermissionMixin, TemplateView):
    """Admin welcome view."""

    template_name = "adminsec/overview.html"
    permission_required = "adminsec.is_hpcadmin"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add open HpcGroupCreateRequest
        context["hpcgroupcreaterequests"] = HpcGroupCreateRequest.objects.active()

        # TODO: Add other open requests

        return context


class HpcGroupCreateRequestDetailView(HpcPermissionMixin, DetailView):
    """Pending group request detail view."""

    template_name = "usersec/hpcgroupcreaterequest_detail.html"
    model = HpcGroupCreateRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupcreaterequest"
    permission_required = "adminsec.is_hpcadmin"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context["comment_history"] = obj.get_comment_history()
        context["is_denied"] = obj.is_denied()
        context["is_retracted"] = obj.is_retracted()
        context["is_approved"] = obj.is_approved()
        context["is_decided"] = obj.is_decided()
        context["admin"] = True
        return context


class HpcGroupCreateRequestRevisionView(HpcPermissionMixin, UpdateView):
    """Pending group request revision view."""

    # Using template from usersec
    template_name = "usersec/hpcgroupcreaterequest_form.html"
    model = HpcGroupCreateRequest
    form_class = HpcGroupCreateRequestForm
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupcreaterequest"
    permission_required = "adminsec.is_hpcadmin"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context["update"] = True
        context["comment_history"] = obj.get_comment_history()
        context["admin"] = True
        return context

    def get_success_url(self):
        return reverse(
            "adminsec:hpcgroupcreaterequest-detail",
            kwargs={"hpcgroupcreaterequest": self.get_object().uuid},
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        initial["comment"] = ""
        return initial

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.editor = self.request.user
        obj = obj.revision_with_version()

        if not obj:
            messages.error(self.request, "Couldn't update group request.")
            return HttpResponseRedirect(reverse("adminsec:overview"))

        messages.success(self.request, "Revision requested.")
        return HttpResponseRedirect(self.get_success_url())


class HpcGroupCreateRequestApproveView(HpcPermissionMixin, DeleteView):
    """HpcGroupCreateRequest approve view."""

    template_name_suffix = "_approve_confirm"
    model = HpcGroupCreateRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupcreaterequest"
    permission_required = "adminsec.is_hpcadmin"

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.comment = "Request approved"
        obj.editor = self.request.user
        obj.approve_with_version()
        surname = obj.requester.name.rsplit(" ", 1)[1]

        # Create HpcGroup object
        hpcgroup = HpcGroup.objects.create_with_version(
            resources_requested=obj.resources_requested,
            description=obj.description,
            creator=self.request.user,
            name=generate_hpc_groupname(surname),
            expiration=obj.expiration,
        )

        # Create HpcUser object
        hpcuser = HpcUser.objects.create_with_version(
            user=obj.requester,
            primary_group=hpcgroup,
            resources_requested={"some": "default"},
            creator=self.request.user,
            description="PI, created together with accepting the group request.",
            username=generate_hpc_username(obj.requester.username),
            expiration=timezone.now() + timedelta(weeks=52),
            # TODO phone
        )

        hpcgroup.owner = hpcuser
        hpcgroup.status = OBJECT_STATUS_ACTIVE
        hpcgroup.save()  # We do not need another version for this action.

        messages.success(self.request, "Request approved and group and user created.")
        return HttpResponseRedirect(
            reverse(
                "adminsec:hpcgroupcreaterequest-detail",
                kwargs={"hpcgroupcreaterequest": obj.uuid},
            )
        )


class HpcGroupCreateRequestDenyView(HpcPermissionMixin, DeleteView):
    """Pending group request update view."""

    template_name_suffix = "_deny_confirm"
    model = HpcGroupCreateRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupcreaterequest"
    permission_required = "adminsec.is_hpcadmin"

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["form"] = HpcGroupCreateRequestForm(
            user=self.request.user,
            instance=context["object"],
            initial={
                "comment": "",
            },
        )
        return context

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.comment = self.request.POST.get("comment")
        obj.editor = self.request.user
        obj.deny_with_version()
        messages.success(self.request, "Request successfully denied.")
        return HttpResponseRedirect(
            reverse(
                "adminsec:hpcgroupcreaterequest-detail",
                kwargs={"hpcgroupcreaterequest": obj.uuid},
            )
        )
