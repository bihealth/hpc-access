import unicodedata
from datetime import timedelta


from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import (
    DetailView,
    UpdateView,
    DeleteView,
    TemplateView,
)

from adminsec.email import (
    send_user_invite,
    send_user_added_to_project_notification,
    send_project_created_notification,
)
from adminsec.ldap import LdapConnector
from usersec.forms import (
    HpcGroupCreateRequestForm,
    HpcUserCreateRequestForm,
    HpcProjectCreateRequestForm,
)
from usersec.models import (
    HpcGroupCreateRequest,
    HpcGroup,
    HpcUser,
    OBJECT_STATUS_ACTIVE,
    HpcUserCreateRequest,
    OBJECT_STATUS_INITIAL,
    HpcProject,
    HpcProjectCreateRequest,
    HpcGroupVersion,
)
from usersec.views import HpcPermissionMixin


LDAP_ENABLED = getattr(settings, "ENABLE_LDAP")
# Required for LDAP2
LDAP2_ENABLED = getattr(settings, "ENABLE_LDAP_SECONDARY")

DOMAIN_MAPPING = {}

if LDAP_ENABLED:
    LDAP_DOMAIN = getattr(settings, "AUTH_LDAP_USERNAME_DOMAIN")
    INSTITUTE_USERNAME_SUFFIX = getattr(settings, "INSTITUTE_USERNAME_SUFFIX")
    DOMAIN_MAPPING[LDAP_DOMAIN] = INSTITUTE_USERNAME_SUFFIX

if LDAP2_ENABLED:
    LDAP2_DOMAIN = getattr(settings, "AUTH_LDAP2_USERNAME_DOMAIN")
    INSTITUTE2_USERNAME_SUFFIX = getattr(settings, "INSTITUTE2_USERNAME_SUFFIX")
    DOMAIN_MAPPING[LDAP2_DOMAIN] = INSTITUTE2_USERNAME_SUFFIX

AG_PREFIX = "ag_"
LDAP_USERNAME_SEPARATOR = "@"
HPC_USERNAME_SEPARATOR = "_"


def ldap_to_hpc_username(username, domain):
    fail_string = ""
    ending = DOMAIN_MAPPING.get(domain.upper())

    if not ending:
        return fail_string

    return f"{username}{HPC_USERNAME_SEPARATOR}{ending}"


def django_to_hpc_username(username):
    fail_string = ""
    data = username.split(LDAP_USERNAME_SEPARATOR)

    if not len(data) == 2:
        return fail_string

    username, domain = data

    return ldap_to_hpc_username(username, domain)


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

        # Used as switch in template
        context["admin"] = True

        # Add open HpcGroupCreateRequest
        context["hpcgroupcreaterequests"] = HpcGroupCreateRequest.objects.active()

        # Add open HpcUserCreateRequest
        context["hpcusercreaterequests"] = HpcUserCreateRequest.objects.active()

        # Add open HpcProjectCreateRequest
        context["hpcprojectcreaterequests"] = HpcProjectCreateRequest.objects.active()

        # Add open HpcUserChangeRequest
        context["hpcuserchangerequests"] = None

        # Add open HpcGroupChangeRequest
        context["hpcgroupchangerequests"] = None

        # Add open HpcProjectChangeRequest
        context["hpcprojectchangerequests"] = None

        # Add open HpcGroupDeleteRequest
        context["hpcgroupdeleterequests"] = None

        # Add open HpcUserDeleteRequest
        context["hpcuserdeleterequests"] = None

        # Add open HpcProjectDeleteRequest
        context["hpcprojectdeleterequests"] = None

        return context


class HpcGroupDetailView(HpcPermissionMixin, DetailView):
    """HPC group view."""

    model = HpcGroup
    template_name = "usersec/hpcgroup_detail.html"
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroup"
    permission_required = "adminsec.is_hpcadmin"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["admin"] = True
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
        context["is_decided"] = obj.is_decided()
        context["is_denied"] = obj.is_denied()
        context["is_retracted"] = obj.is_retracted()
        context["is_approved"] = obj.is_approved()
        context["is_active"] = obj.is_active()
        context["is_revision"] = obj.is_revision()
        context["is_revised"] = obj.is_revised()
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
        context["update"] = True
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
            username=django_to_hpc_username(obj.requester.username),
            status=OBJECT_STATUS_ACTIVE,
            expiration=timezone.now() + timedelta(weeks=52),
        )

        # Set group owner
        hpcgroup.owner = hpcuser
        hpcgroup.status = OBJECT_STATUS_ACTIVE
        hpcgroup.save()  # We do not need another version for this action.

        # Set group owner in versino object
        hpcgroup_version = HpcGroupVersion.objects.get(belongs_to=hpcgroup)
        hpcgroup_version.owner = hpcuser
        hpcgroup.status = OBJECT_STATUS_ACTIVE
        hpcgroup_version.save()

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


class HpcUserDetailView(HpcPermissionMixin, DetailView):
    """HPC user detail view."""

    model = HpcUser
    template_name = "usersec/hpcuser_detail.html"
    slug_field = "uuid"
    slug_url_kwarg = "hpcuser"
    permission_required = "adminsec.is_hpcadmin"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["admin"] = True
        return context


class HpcUserCreateRequestDetailView(HpcPermissionMixin, DetailView):
    """HPC user create request detail view."""

    template_name = "usersec/hpcusercreaterequest_detail.html"
    model = HpcUserCreateRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcusercreaterequest"
    permission_required = "adminsec.is_hpcadmin"

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
        context["admin"] = True
        return context


class HpcUserCreateRequestRevisionView(HpcPermissionMixin, UpdateView):
    """HPC user create request revision view."""

    template_name = "usersec/hpcusercreaterequest_form.html"
    model = HpcUserCreateRequest
    form_class = HpcUserCreateRequestForm
    slug_field = "uuid"
    slug_url_kwarg = "hpcusercreaterequest"
    permission_required = "adminsec.is_hpcadmin"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["update"] = True
        context["admin"] = True
        return context

    def get_success_url(self):
        return reverse(
            "adminsec:hpcusercreaterequest-detail",
            kwargs={"hpcusercreaterequest": self.get_object().uuid},
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
            messages.error(self.request, "Couldn't update user request.")
            return HttpResponseRedirect(reverse("adminsec:overview"))

        messages.success(self.request, "Revision requested.")
        return HttpResponseRedirect(self.get_success_url())


class HpcUserCreateRequestApproveView(HpcPermissionMixin, DeleteView):
    """HpcUserCreateRequest approve view."""

    template_name_suffix = "_approve_confirm"
    model = HpcUserCreateRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcusercreaterequest"
    permission_required = "adminsec.is_hpcadmin"

    def post(self, request, *args, **kwargs):
        obj = self.get_object()

        try:
            ldapcon = LdapConnector()
            ldapcon.connect()
            username, domain = ldapcon.get_ldap_username_domain_by_mail(obj.email)

        except Exception as e:
            messages.error(self.request, "There was an error with the LDAP: {}".format(e))
            return HttpResponseRedirect(
                reverse(
                    "adminsec:hpcusercreaterequest-detail",
                    kwargs={"hpcusercreaterequest": obj.uuid},
                )
            )

        try:
            with transaction.atomic():
                HpcUser.objects.create_with_version(
                    user=None,
                    primary_group=obj.group,
                    resources_requested=obj.resources_requested,
                    creator=self.request.user,
                    username=ldap_to_hpc_username(username, domain),
                    status=OBJECT_STATUS_INITIAL,
                    expiration=obj.expiration,
                )

        except Exception as e:
            messages.error(self.request, "Could not create user object: {}".format(e))
            return HttpResponseRedirect(
                reverse(
                    "adminsec:hpcusercreaterequest-detail",
                    kwargs={"hpcusercreaterequest": obj.uuid},
                )
            )

        if settings.SEND_EMAIL:
            send_user_invite(
                recipient_list=[obj.email],
                inviter=obj.requester.hpcuser_user.first(),
                request=self.request,
            )

        with transaction.atomic():
            obj.comment = "Request approved"
            obj.editor = self.request.user
            obj.approve_with_version()

        messages.success(self.request, "Request approved and user created.")
        return HttpResponseRedirect(
            reverse(
                "adminsec:hpcusercreaterequest-detail",
                kwargs={"hpcusercreaterequest": obj.uuid},
            )
        )


class HpcUserCreateRequestDenyView(HpcPermissionMixin, DeleteView):
    """HpcUserCreateRequest deny view."""

    template_name_suffix = "_deny_confirm"
    model = HpcUserCreateRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcusercreaterequest"
    permission_required = "adminsec.is_hpcadmin"

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["form"] = HpcUserCreateRequestForm(
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
                "adminsec:hpcusercreaterequest-detail",
                kwargs={"hpcusercreaterequest": obj.uuid},
            )
        )


class HpcGroupDeleteRequestDetailView(View):
    pass


class HpcGroupDeleteRequestRevisionView(View):
    pass


class HpcGroupDeleteRequestApproveView(View):
    pass


class HpcGroupDeleteRequestDenyView(View):
    pass


class HpcGroupChangeRequestDetailView(View):
    pass


class HpcGroupChangeRequestRevisionView(View):
    pass


class HpcGroupChangeRequestApproveView(View):
    pass


class HpcGroupChangeRequestDenyView(View):
    pass


class HpcProjectDetailView(HpcPermissionMixin, DetailView):
    """HpcProjectDetail view."""

    model = HpcProject
    template_name = "usersec/hpcproject_detail.html"
    slug_field = "uuid"
    slug_url_kwarg = "hpcproject"
    permission_required = "adminsec.is_hpcadmin"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["admin"] = True
        return context


class HpcProjectCreateRequestDetailView(HpcPermissionMixin, DetailView):
    """HpcProjectCreateRequestDetail view."""

    template_name = "usersec/hpcprojectcreaterequest_detail.html"
    model = HpcProjectCreateRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcprojectcreaterequest"
    permission_required = "adminsec.is_hpcadmin"

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
        context["admin"] = True
        return context


class HpcProjectCreateRequestRevisionView(HpcPermissionMixin, UpdateView):
    """HpcProjectCreateRequestRevision view."""

    template_name = "usersec/hpcprojectcreaterequest_form.html"
    model = HpcProjectCreateRequest
    form_class = HpcProjectCreateRequestForm
    slug_field = "uuid"
    slug_url_kwarg = "hpcprojectcreaterequest"
    permission_required = "adminsec.is_hpcadmin"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["update"] = True
        context["admin"] = True
        return context

    def get_success_url(self):
        return reverse(
            "adminsec:hpcprojectcreaterequest-detail",
            kwargs={"hpcprojectcreaterequest": self.get_object().uuid},
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
            messages.error(self.request, "Couldn't update project request.")
            return HttpResponseRedirect(reverse("adminsec:overview"))

        messages.success(self.request, "Revision requested.")
        return HttpResponseRedirect(self.get_success_url())


class HpcProjectCreateRequestApproveView(HpcPermissionMixin, DeleteView):
    """HpcProjectCreateRequest approve view."""

    template_name_suffix = "_approve_confirm"
    model = HpcProjectCreateRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcprojectcreaterequest"
    permission_required = "adminsec.is_hpcadmin"

    def post(self, request, *args, **kwargs):
        obj = self.get_object()

        try:
            with transaction.atomic():
                project = HpcProject.objects.create_with_version(
                    group=obj.group,
                    name=obj.name,
                    delegate=obj.delegate,
                    description=obj.description,
                    resources_requested=obj.resources_requested,
                    creator=self.request.user,
                    status=OBJECT_STATUS_ACTIVE,
                    expiration=obj.expiration,
                )
                project.members.set(obj.members.all())
                project.version_history.last().members.set(obj.members.all())

        except Exception as e:
            messages.error(self.request, "Could not create project object: {}".format(e))
            return HttpResponseRedirect(
                reverse(
                    "adminsec:hpcprojectcreaterequest-detail",
                    kwargs={"hpcprojectcreaterequest": obj.uuid},
                )
            )

        if settings.SEND_EMAIL:
            send_user_added_to_project_notification(
                project=project,
                request=self.request,
            )
            send_project_created_notification(
                project=project,
                request=self.request,
            )

        with transaction.atomic():
            obj.comment = "Request approved"
            obj.editor = self.request.user
            obj.approve_with_version()

        messages.success(self.request, "Request approved and project created.")
        return HttpResponseRedirect(
            reverse(
                "adminsec:hpcprojectcreaterequest-detail",
                kwargs={"hpcprojectcreaterequest": obj.uuid},
            )
        )


class HpcProjectCreateRequestDenyView(HpcPermissionMixin, DeleteView):
    """HpcProjectCreateRequest deny view."""

    template_name_suffix = "_deny_confirm"
    model = HpcProjectCreateRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcprojectcreaterequest"
    permission_required = "adminsec.is_hpcadmin"

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["form"] = HpcProjectCreateRequestForm(
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
                "adminsec:hpcprojectcreaterequest-detail",
                kwargs={"hpcprojectcreaterequest": obj.uuid},
            )
        )


class HpcUserDeleteRequestDetailView(View):
    pass


class HpcUserDeleteRequestRevisionView(View):
    pass


class HpcUserDeleteRequestApproveView(View):
    pass


class HpcUserDeleteRequestDenyView(View):
    pass


class HpcUserChangeRequestDetailView(View):
    pass


class HpcUserChangeRequestRevisionView(View):
    pass


class HpcUserChangeRequestApproveView(View):
    pass


class HpcUserChangeRequestDenyView(View):
    pass


class HpcProjectDeleteRequestDetailView(View):
    pass


class HpcProjectDeleteRequestRevisionView(View):
    pass


class HpcProjectDeleteRequestApproveView(View):
    pass


class HpcProjectDeleteRequestDenyView(View):
    pass


class HpcProjectChangeRequestDetailView(View):
    pass


class HpcProjectChangeRequestRevisionView(View):
    pass


class HpcProjectChangeRequestApproveView(View):
    pass


class HpcProjectChangeRequestDenyView(View):
    pass
