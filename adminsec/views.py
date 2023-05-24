import unicodedata

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.datetime_safe import datetime
from django.views import View
from django.views.generic import DeleteView, DetailView, TemplateView, UpdateView

from adminsec.email import (
    send_notification_manager_change_request_approved,
    send_notification_manager_group_created,
    send_notification_manager_project_created,
    send_notification_manager_request_denied,
    send_notification_manager_revision_required,
    send_notification_user_invitation,
    send_notification_user_welcome_mail,
)
from adminsec.ldap import LdapConnector
from hpcaccess.users.models import User
from usersec.forms import (
    DEFAULT_USER_RESOURCES,
    HpcGroupChangeRequestForm,
    HpcGroupCreateRequestForm,
    HpcProjectChangeRequestForm,
    HpcProjectCreateRequestForm,
    HpcUserChangeRequestForm,
    HpcUserCreateRequestForm,
)
from usersec.models import (
    OBJECT_STATUS_ACTIVE,
    HpcGroup,
    HpcGroupChangeRequest,
    HpcGroupCreateRequest,
    HpcGroupInvitation,
    HpcGroupVersion,
    HpcProject,
    HpcProjectChangeRequest,
    HpcProjectCreateRequest,
    HpcProjectInvitation,
    HpcUser,
    HpcUserChangeRequest,
    HpcUserCreateRequest,
)
from usersec.views import (
    MSG_PART_GROUP_CREATION,
    MSG_PART_GROUP_UPDATE,
    MSG_PART_PROJECT_CREATION,
    MSG_PART_PROJECT_UPDATE,
    MSG_PART_SUBMIT,
    MSG_PART_UPDATE,
    MSG_PART_USER_CREATION,
    MSG_PART_USER_UPDATE,
    MSG_REQUEST_FAILURE,
    HpcPermissionMixin,
)

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

# ------------------------------------------------------------------------------
# UI message texts
# ------------------------------------------------------------------------------

#: Message to show on successfully requesting a revision
MSG_REQUEST_REVISION_SUCCESS = "Successfully requested revision for {}."

#: Message to show on failing to request a revision
MSG_REQUEST_REVISION_FAILURE = "Couldn't request revision for {}."

#: Message to show on successfully approving a request
MSG_REQUEST_APPROVED_SUCCESS = "Successfully approved request for {}."

#: Message to show on successfully denying a request
MSG_REQUEST_DENIED_SUCCESS = "Successfully denied request for {}."

#: Message to show on failing a request
MSG_REQUEST_FAILURE_WITH_ERROR = MSG_REQUEST_FAILURE + " Error: {}"

# -----------------------------------------------------------------------------
# Object comments
# -----------------------------------------------------------------------------

#: Object comment text for an approved request
COMMENT_APPROVED = "Request approved"


def get_admin_emails():
    return [u.email for u in User.objects.filter(is_hpcadmin=True, email__isnull=False)]


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


def ldap_to_django_username(username, domain):
    return f"{username}{LDAP_USERNAME_SEPARATOR}{domain}"


def convert_to_posix(name):
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")


# TODO this should be just a suggestion and the field should be editable
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
        context["hpcuserchangerequests"] = HpcUserChangeRequest.objects.active()

        # Add open HpcGroupChangeRequest
        context["hpcgroupchangerequests"] = HpcGroupChangeRequest.objects.active()

        # Add open HpcProjectChangeRequest
        context["hpcprojectchangerequests"] = HpcProjectChangeRequest.objects.active()

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
    success_url = reverse_lazy("adminsec:overview")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["update"] = True
        context["admin"] = True
        return context

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
            messages.error(
                self.request, MSG_REQUEST_REVISION_FAILURE.format(MSG_PART_GROUP_CREATION)
            )
            return HttpResponseRedirect(reverse("adminsec:overview"))

        if settings.SEND_EMAIL:
            send_notification_manager_revision_required(obj)

        messages.success(self.request, MSG_REQUEST_REVISION_SUCCESS.format(MSG_PART_GROUP_CREATION))
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
            resources_requested=DEFAULT_USER_RESOURCES,
            creator=self.request.user,
            description="PI, created together with accepting the group request.",
            username=django_to_hpc_username(obj.requester.username),
            status=OBJECT_STATUS_ACTIVE,
            expiration=datetime(year=timezone.now().year + 1, month=1, day=31),
        )

        # Set group owner
        hpcgroup.owner = hpcuser
        hpcgroup.status = OBJECT_STATUS_ACTIVE
        hpcgroup.save()  # We do not need another version for this action.

        # Set group owner in version object
        hpcgroup_version = HpcGroupVersion.objects.get(belongs_to=hpcgroup)
        hpcgroup_version.owner = hpcuser
        hpcgroup.status = OBJECT_STATUS_ACTIVE
        hpcgroup_version.save()

        if settings.SEND_EMAIL:
            send_notification_manager_group_created(obj, hpcgroup)
            send_notification_user_welcome_mail(hpcuser)

        obj.comment = COMMENT_APPROVED
        obj.editor = self.request.user
        obj.approve_with_version()

        messages.success(self.request, MSG_REQUEST_APPROVED_SUCCESS.format(MSG_PART_GROUP_CREATION))
        return HttpResponseRedirect(reverse("adminsec:overview"))


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

        if settings.SEND_EMAIL:
            send_notification_manager_request_denied(obj)

        messages.success(self.request, MSG_REQUEST_DENIED_SUCCESS.format(MSG_PART_GROUP_CREATION))
        return HttpResponseRedirect(reverse("adminsec:overview"))


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
    success_url = reverse_lazy("adminsec:overview")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["update"] = True
        context["admin"] = True
        return context

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
            messages.error(
                self.request, MSG_REQUEST_REVISION_FAILURE.format(MSG_PART_USER_CREATION)
            )
            return HttpResponseRedirect(reverse("adminsec:overview"))

        if settings.SEND_EMAIL:
            send_notification_manager_revision_required(obj)

        messages.success(self.request, MSG_REQUEST_REVISION_SUCCESS.format(MSG_PART_USER_CREATION))
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
                invitation = HpcGroupInvitation.objects.create_with_version(
                    hpcusercreaterequest=obj, username=ldap_to_django_username(username, domain)
                )

        except Exception as e:
            messages.error(self.request, "Could not create invitation object: {}".format(e))
            return HttpResponseRedirect(
                reverse(
                    "adminsec:hpcusercreaterequest-detail",
                    kwargs={"hpcusercreaterequest": obj.uuid},
                )
            )

        if settings.SEND_EMAIL:
            send_notification_user_invitation(invitation)

        obj.comment = COMMENT_APPROVED
        obj.editor = self.request.user
        obj.approve_with_version()

        messages.success(self.request, "Request approved and invitation created.")
        return HttpResponseRedirect(reverse("adminsec:overview"))


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

        if settings.SEND_EMAIL:
            send_notification_manager_request_denied(obj)

        messages.success(self.request, MSG_REQUEST_DENIED_SUCCESS.format(MSG_PART_USER_CREATION))
        return HttpResponseRedirect(reverse("adminsec:overview"))


class HpcGroupDeleteRequestDetailView(View):
    pass


class HpcGroupDeleteRequestRevisionView(View):
    pass


class HpcGroupDeleteRequestApproveView(View):
    pass


class HpcGroupDeleteRequestDenyView(View):
    pass


class HpcGroupChangeRequestDetailView(HpcPermissionMixin, DetailView):
    """HPC group change request detail view."""

    template_name = "usersec/hpcgroupchangerequest_detail.html"
    model = HpcGroupChangeRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupchangerequest"
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


class HpcGroupChangeRequestRevisionView(HpcPermissionMixin, UpdateView):
    """HPC group change request revision view."""

    template_name = "usersec/hpcgroupchangerequest_form.html"
    model = HpcGroupChangeRequest
    form_class = HpcGroupChangeRequestForm
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupchangerequest"
    permission_required = "adminsec.is_hpcadmin"
    success_url = reverse_lazy("adminsec:overview")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["update"] = True
        context["admin"] = True
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user, "group": self.get_object().group})
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
            messages.error(self.request, MSG_REQUEST_REVISION_FAILURE.format(MSG_PART_GROUP_UPDATE))
            return HttpResponseRedirect(reverse("adminsec:overview"))

        if settings.SEND_EMAIL:
            send_notification_manager_revision_required(obj)

        messages.success(self.request, MSG_REQUEST_REVISION_SUCCESS.format(MSG_PART_GROUP_UPDATE))
        return HttpResponseRedirect(self.get_success_url())


class HpcGroupChangeRequestApproveView(HpcPermissionMixin, DeleteView):
    """HpcGroupChangeRequest approve view."""

    template_name_suffix = "_approve_confirm"
    model = HpcGroupChangeRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupchangerequest"
    permission_required = "adminsec.is_hpcadmin"
    success_url = reverse_lazy("adminsec:overview")

    def post(self, request, *args, **kwargs):
        obj = self.get_object()

        try:
            with transaction.atomic():
                obj.group.update_with_version(
                    delegate=obj.delegate,
                    expiration=obj.expiration,
                    resources_requested=obj.resources_requested,
                    description=obj.description,
                )

        except Exception as e:
            messages.error(
                self.request,
                MSG_REQUEST_FAILURE_WITH_ERROR.format(MSG_PART_UPDATE, MSG_PART_GROUP_UPDATE, e),
            )
            return HttpResponseRedirect(
                reverse(
                    "adminsec:hpcgroupchangerequest-detail",
                    kwargs={"hpcgroupchangerequest": obj.uuid},
                )
            )

        if settings.SEND_EMAIL:
            send_notification_manager_change_request_approved(obj)

        with transaction.atomic():
            obj.comment = COMMENT_APPROVED
            obj.editor = self.request.user
            obj.approve_with_version()

        messages.success(self.request, MSG_REQUEST_APPROVED_SUCCESS.format(MSG_PART_GROUP_UPDATE))
        return HttpResponseRedirect(reverse("adminsec:overview"))


class HpcGroupChangeRequestDenyView(HpcPermissionMixin, DeleteView):
    """HpcGroupChangeRequest deny view."""

    template_name_suffix = "_deny_confirm"
    model = HpcGroupChangeRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupchangerequest"
    permission_required = "adminsec.is_hpcadmin"

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["form"] = HpcGroupChangeRequestForm(
            user=self.request.user,
            group=context["object"].group,
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

        if settings.SEND_EMAIL:
            send_notification_manager_request_denied(obj)

        messages.success(self.request, MSG_REQUEST_DENIED_SUCCESS.format(MSG_PART_GROUP_UPDATE))
        return HttpResponseRedirect(reverse("adminsec:overview"))


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
    success_url = reverse_lazy("adminsec:overview")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["update"] = True
        context["admin"] = True
        return context

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
            messages.error(
                self.request, MSG_REQUEST_REVISION_FAILURE.format(MSG_PART_PROJECT_CREATION)
            )
            return HttpResponseRedirect(reverse("adminsec:overview"))

        if settings.SEND_EMAIL:
            send_notification_manager_revision_required(obj)

        messages.success(
            self.request, MSG_REQUEST_REVISION_SUCCESS.format(MSG_PART_PROJECT_CREATION)
        )
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
                    description=obj.description,
                    resources_requested=obj.resources_requested,
                    creator=self.request.user,
                    status=OBJECT_STATUS_ACTIVE,
                    expiration=obj.expiration,
                )
                project.members.add(obj.group.owner)
                project.version_history.last().members.add(obj.group.owner)

                # Create invitations for users
                for member in obj.members.all():
                    if member == obj.group.owner:
                        continue

                    invitation = HpcProjectInvitation.objects.create_with_version(
                        project=project,
                        hpcprojectcreaterequest=obj,
                        user=member,
                    )

                    if settings.SEND_EMAIL:
                        send_notification_user_invitation(invitation)

        except Exception as e:
            messages.error(
                self.request,
                MSG_REQUEST_FAILURE_WITH_ERROR.format(
                    MSG_PART_SUBMIT, MSG_PART_PROJECT_CREATION, e
                ),
            )
            return HttpResponseRedirect(
                reverse(
                    "adminsec:hpcprojectcreaterequest-detail",
                    kwargs={"hpcprojectcreaterequest": obj.uuid},
                )
            )

        if settings.SEND_EMAIL:
            send_notification_manager_project_created(obj, project)

        with transaction.atomic():
            obj.comment = COMMENT_APPROVED
            obj.editor = self.request.user
            obj.approve_with_version()

        messages.success(
            self.request, MSG_REQUEST_APPROVED_SUCCESS.format(MSG_PART_PROJECT_CREATION)
        )
        return HttpResponseRedirect(reverse("adminsec:overview"))


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

        if settings.SEND_EMAIL:
            # TODO email to user: project denied.
            send_notification_manager_request_denied(obj)

        messages.success(self.request, "Request successfully denied.")
        return HttpResponseRedirect(reverse("adminsec:overview"))


class HpcUserDeleteRequestDetailView(View):
    pass


class HpcUserDeleteRequestRevisionView(View):
    pass


class HpcUserDeleteRequestApproveView(View):
    pass


class HpcUserDeleteRequestDenyView(View):
    pass


class HpcUserChangeRequestDetailView(HpcPermissionMixin, DetailView):
    """HPC user change request detail view."""

    template_name = "usersec/hpcuserchangerequest_detail.html"
    model = HpcUserChangeRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcuserchangerequest"
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


class HpcUserChangeRequestRevisionView(HpcPermissionMixin, UpdateView):
    """HPC user change request revision view."""

    template_name = "usersec/hpcuserchangerequest_form.html"
    model = HpcUserChangeRequest
    form_class = HpcUserChangeRequestForm
    slug_field = "uuid"
    slug_url_kwarg = "hpcuserchangerequest"
    permission_required = "adminsec.is_hpcadmin"
    success_url = reverse_lazy("adminsec:overview")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["update"] = True
        context["admin"] = True
        return context

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
            messages.error(self.request, MSG_REQUEST_REVISION_FAILURE.format(MSG_PART_USER_UPDATE))
            return HttpResponseRedirect(reverse("adminsec:overview"))

        if settings.SEND_EMAIL:
            send_notification_manager_revision_required(obj)

        messages.success(self.request, MSG_REQUEST_REVISION_SUCCESS.format(MSG_PART_USER_UPDATE))
        return HttpResponseRedirect(self.get_success_url())


class HpcUserChangeRequestApproveView(HpcPermissionMixin, DeleteView):
    """HpcUserChangeRequest approve view."""

    template_name_suffix = "_approve_confirm"
    model = HpcUserChangeRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcuserchangerequest"
    permission_required = "adminsec.is_hpcadmin"
    success_url = reverse_lazy("adminsec:overview")

    def post(self, request, *args, **kwargs):
        obj = self.get_object()

        try:
            with transaction.atomic():
                obj.user.update_with_version(expiration=obj.expiration)

        except Exception as e:
            messages.error(self.request, "Could not update user: {}".format(e))
            return HttpResponseRedirect(
                reverse(
                    "adminsec:hpcuserchangerequest-detail",
                    kwargs={"hpcuserchangerequest": obj.uuid},
                )
            )

        with transaction.atomic():
            obj.comment = COMMENT_APPROVED
            obj.editor = self.request.user
            obj.approve_with_version()

        if settings.SEND_EMAIL:
            send_notification_manager_change_request_approved(obj)

        messages.success(self.request, MSG_REQUEST_APPROVED_SUCCESS.format(MSG_PART_USER_UPDATE))
        return HttpResponseRedirect(reverse("adminsec:overview"))


class HpcUserChangeRequestDenyView(HpcPermissionMixin, DeleteView):
    """HpcGroupChangeRequest deny view."""

    template_name_suffix = "_deny_confirm"
    model = HpcUserChangeRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcuserchangerequest"
    permission_required = "adminsec.is_hpcadmin"

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["form"] = HpcUserChangeRequestForm(
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

        if settings.SEND_EMAIL:
            send_notification_manager_request_denied(obj)

        messages.success(self.request, MSG_REQUEST_DENIED_SUCCESS.format(MSG_PART_USER_UPDATE))
        return HttpResponseRedirect(reverse("adminsec:overview"))


class HpcProjectDeleteRequestDetailView(View):
    pass


class HpcProjectDeleteRequestRevisionView(View):
    pass


class HpcProjectDeleteRequestApproveView(View):
    pass


class HpcProjectDeleteRequestDenyView(View):
    pass


class HpcProjectChangeRequestDetailView(HpcPermissionMixin, DetailView):
    """HPC project change request detail view."""

    template_name = "usersec/hpcprojectchangerequest_detail.html"
    model = HpcProjectChangeRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcprojectchangerequest"
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


class HpcProjectChangeRequestRevisionView(HpcPermissionMixin, UpdateView):
    """HPC project change request revision view."""

    template_name = "usersec/hpcprojectchangerequest_form.html"
    model = HpcProjectChangeRequest
    form_class = HpcProjectChangeRequestForm
    slug_field = "uuid"
    slug_url_kwarg = "hpcprojectchangerequest"
    permission_required = "adminsec.is_hpcadmin"
    success_url = reverse_lazy("adminsec:overview")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["update"] = True
        context["admin"] = True
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user, "project": self.get_object().project})
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
            messages.error(
                self.request, MSG_REQUEST_REVISION_FAILURE.format(MSG_PART_PROJECT_UPDATE)
            )
            return HttpResponseRedirect(reverse("adminsec:overview"))

        if settings.SEND_EMAIL:
            send_notification_manager_revision_required(obj)

        messages.success(self.request, MSG_REQUEST_REVISION_SUCCESS.format(MSG_PART_PROJECT_UPDATE))
        return HttpResponseRedirect(self.get_success_url())


class HpcProjectChangeRequestApproveView(HpcPermissionMixin, DeleteView):
    """HpcProjectChangeRequest approve view."""

    template_name_suffix = "_approve_confirm"
    model = HpcProjectChangeRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcprojectchangerequest"
    permission_required = "adminsec.is_hpcadmin"
    success_url = reverse_lazy("adminsec:overview")

    def post(self, request, *args, **kwargs):
        obj = self.get_object()

        try:
            with transaction.atomic():
                obj.project.update_with_version(
                    delegate=obj.delegate,
                    expiration=obj.expiration,
                    resources_requested=obj.resources_requested,
                    description=obj.description,
                )

                for member in obj.members.all():
                    if obj.project.members.filter(id=member.id).exists():
                        continue

                    invitation = HpcProjectInvitation.objects.create_with_version(
                        project=obj.project,
                        hpcprojectchangerequest=obj,
                        user=member,
                    )

                    if settings.SEND_EMAIL:
                        send_notification_user_invitation(invitation)

                for member in obj.project.members.all():
                    if obj.members.filter(id=member.id).exists():
                        obj.project.get_latest_version().members.add(member)
                        continue

                    obj.project.members.remove(member)

        except Exception as e:
            messages.error(
                self.request,
                MSG_REQUEST_FAILURE_WITH_ERROR.format(MSG_PART_UPDATE, MSG_PART_PROJECT_UPDATE, e),
            )
            return HttpResponseRedirect(
                reverse(
                    "adminsec:hpcprojectchangerequest-detail",
                    kwargs={"hpcprojectchangerequest": obj.uuid},
                )
            )

        with transaction.atomic():
            obj.comment = COMMENT_APPROVED
            obj.editor = self.request.user
            obj.approve_with_version()

        if settings.SEND_EMAIL:
            send_notification_manager_change_request_approved(obj)

        messages.success(self.request, MSG_REQUEST_APPROVED_SUCCESS.format(MSG_PART_PROJECT_UPDATE))
        return HttpResponseRedirect(reverse("adminsec:overview"))


class HpcProjectChangeRequestDenyView(HpcPermissionMixin, DeleteView):
    """HpcProjectChangeRequest deny view."""

    template_name_suffix = "_deny_confirm"
    model = HpcProjectChangeRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcprojectchangerequest"
    permission_required = "adminsec.is_hpcadmin"

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["form"] = HpcProjectChangeRequestForm(
            user=self.request.user,
            project=context["object"].project,
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

        if settings.SEND_EMAIL:
            send_notification_manager_request_denied(obj)

        messages.success(self.request, MSG_REQUEST_DENIED_SUCCESS.format(MSG_PART_PROJECT_UPDATE))
        return HttpResponseRedirect(reverse("adminsec:overview"))
