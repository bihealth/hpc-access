import re
from datetime import datetime

import rules
from django import forms
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from adminsec.constants import (
    DEFAULT_GROUP_RESOURCES,
    DEFAULT_PROJECT_RESOURCES,
    DEFAULT_USER_RESOURCES,
    RE_NAME_CORE,
)
from usersec.models import (
    HpcGroupChangeRequest,
    HpcGroupCreateRequest,
    HpcProject,
    HpcProjectChangeRequest,
    HpcProjectCreateRequest,
    HpcUser,
    HpcUserChangeRequest,
    HpcUserCreateRequest,
)


def build_option(member):
    return (
        str(member.id),
        "{} {} ({}, AG {})".format(
            member.user.first_name,
            member.user.last_name,
            member.username,
            member.primary_group.name,
        ),
    )


def get_project_resource(resource, instance, project=None):
    default = DEFAULT_PROJECT_RESOURCES[resource]

    if project:
        project_resources = project.resources_requested.get(resource, default)
    else:
        project_resources = default

    if instance:
        return instance.resources_requested.get(resource, project_resources)

    return project_resources


class HpcGroupCreateRequestForm(forms.ModelForm):
    """Form for HpcGroupCreateRequest."""

    class Meta:
        model = HpcGroupCreateRequest
        fields = [
            "resources_requested",
            "description",
            "expiration",
            "comment",
        ]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["resources_requested"].widget = forms.HiddenInput()
        self.fields["resources_requested"].initial = DEFAULT_GROUP_RESOURCES
        if self.instance:
            self.fields["description"].initial = self.instance.description

        # Add fields for storage. Will be merged into resources_requested field.
        if not user.is_hpcadmin:
            self.fields["expiration"].disabled = True
            self.fields["expiration"].initial = datetime(
                year=timezone.now().year + 1, month=1, day=31
            )
            self.fields["expiration"].help_text = (
                "Default expiration date is fixed to end of the current year with one month grace "
                "period. It can be extended on request."
            )

        else:
            self.fields["description"].widget = forms.HiddenInput()
            self.fields["expiration"].widget = forms.HiddenInput()
            self.fields["comment"].required = True

        # Some cosmetics
        self.fields["description"].widget.attrs["class"] = "form-control"
        self.fields["expiration"].widget.attrs["class"] = "form-control"
        self.fields["comment"].widget.attrs["class"] = "form-control"
        self.fields["comment"].widget.attrs["rows"] = 3
        self.fields["comment"].help_text = (
            "For the initial group creation request provide some 'proof' that you are a group "
            "leader such as linking to your group website at Charite or MDC. This field is for "
            "communication between you and the HPC team."
        )


class HpcGroupChangeRequestForm(forms.ModelForm):
    """Form for HpcGroupChangeRequest."""

    class Meta:
        model = HpcGroupChangeRequest
        fields = [
            "resources_requested",
            "delegate",
            "description",
            "expiration",
            "comment",
        ]

    def __init__(self, *args, user, group, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["resources_requested"].widget = forms.HiddenInput()
        self.fields["description"].initial = group.description
        self.fields["delegate"].initial = group.delegate
        self.fields["delegate"].queryset = HpcUser.objects.filter(
            primary_group=group, status="ACTIVE"
        ).exclude(id=group.owner.id)

        # Add fields for storage. Will be merged into resources_requested field.
        if not user.is_hpcadmin:
            if group.delegate == user.hpcuser_user.first():
                self.fields["delegate"].widget = forms.HiddenInput()

            self.fields["expiration"].initial = datetime(
                year=timezone.now().year + 1, month=1, day=31
            )
            self.fields["expiration"].help_text = (
                "Default expiration date is set to end of the current year with one month grace "
                "period."
            )

            # Add fields for storage. Will be merged into resources_requested field.
            self.fields["tier1_scratch"] = forms.IntegerField(
                required=True,
                help_text=(
                    "Amount of scratch storage on the fast primary ('tier 1') storage that can be "
                    "used with parallel access for computation."
                ),
                label="Fast Active Storage (Scratch) [TB]",
            )
            self.fields["tier1_scratch"].initial = group.resources_requested["tier1_scratch"]
            self.fields["tier1_scratch"].widget.attrs["class"] = "form-control mergeToJson"

            self.fields["tier1_work"] = forms.IntegerField(
                required=True,
                help_text=(
                    "Amount of work storage on the fast primary ('tier 1') storage that can be "
                    "used with parallel access for computation."
                ),
                label="Fast Active Storage (Work) [TB]",
            )
            self.fields["tier1_work"].initial = group.resources_requested["tier1_work"]
            self.fields["tier1_work"].widget.attrs["class"] = "form-control mergeToJson"

            self.fields["tier2_unmirrored"] = forms.IntegerField(
                required=True,
                help_text=(
                    "Amount of storage on the slower ('tier 2') storage that is meant for "
                    "long-term storage. This storage is not mirrored and should be used for data "
                    "that can be reconstructed from other sources. Alternatively, you can use your "
                    "group storage at Charite or MDC."
                ),
                label="Long-Term Storage (Unmirrored) [TB]",
            )
            self.fields["tier2_unmirrored"].initial = group.resources_requested["tier2_unmirrored"]
            self.fields["tier2_unmirrored"].widget.attrs["class"] = "form-control mergeToJson"

            self.fields["tier2_mirrored"] = forms.IntegerField(
                required=True,
                help_text=(
                    "Amount of storage on the slower ('tier 2') storage that is meant for "
                    "long-term storage. This storage is mirrored and should be used for data that "
                    "cannot be reconstructed from other sources. Alternatively, you can use your "
                    "group storage at Charite or MDC."
                ),
                label="Long-Term Storage (Mirrored) [TB]",
            )
            self.fields["tier2_mirrored"].initial = group.resources_requested["tier2_mirrored"]
            self.fields["tier2_mirrored"].widget.attrs["class"] = "form-control mergeToJson"

        else:
            self.fields["delegate"].widget = forms.HiddenInput()
            self.fields["description"].widget = forms.HiddenInput()
            self.fields["expiration"].widget = forms.HiddenInput()
            self.fields["comment"].required = True

        # Some cosmetics
        self.fields["delegate"].widget.attrs["class"] = "form-control"
        self.fields["description"].widget.attrs["class"] = "form-control"
        self.fields["expiration"].widget.attrs["class"] = "form-control"
        self.fields["comment"].widget.attrs["class"] = "form-control"
        self.fields["comment"].widget.attrs["rows"] = 3


class HpcUserCreateRequestForm(forms.ModelForm):
    """Form for HpcUserCreateRequest."""

    class Meta:
        model = HpcUserCreateRequest
        fields = [
            "resources_requested",
            "expiration",
            "email",
            "comment",
        ]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["resources_requested"].widget = forms.HiddenInput()
        self.fields["resources_requested"].initial = DEFAULT_USER_RESOURCES

        if not user.is_hpcadmin:
            self.fields["expiration"].disabled = True
            self.fields["expiration"].initial = datetime(
                year=timezone.now().year + 1, month=1, day=31
            )
            self.fields["expiration"].help_text = (
                "Default expiration date is fixed to end of the current year with one month grace "
                "period. It can be extended on request."
            )

        else:
            self.fields["email"].widget = forms.HiddenInput()
            self.fields["expiration"].widget = forms.HiddenInput()
            self.fields["comment"].required = True

        # Some cosmetics
        self.fields["email"].widget.attrs["class"] = "form-control"
        self.fields["expiration"].widget.attrs["class"] = "form-control"
        self.fields["comment"].widget.attrs["class"] = "form-control"
        self.fields["comment"].widget.attrs["rows"] = 3

    def clean(self):
        """Override clean to extend the checks."""
        cleaned_data = super().clean()
        email = cleaned_data.get("email")

        if not email:
            return

        email_split = email.split("@")
        valid_domains = []

        if settings.ENABLE_LDAP:
            valid_domains += settings.INSTITUTE_EMAIL_DOMAINS.split(",")

        if settings.ENABLE_LDAP_SECONDARY:
            valid_domains += settings.INSTITUTE2_EMAIL_DOMAINS.split(",")

        if HpcUser.objects.filter(user__email__iexact=email.lower()).exists():
            self.add_error("email", "This user is already registered.")
            return

        if email_split[1].lower() not in valid_domains:
            self.add_error("email", "No institute email address.")
            return

        return cleaned_data


class HpcUserChangeRequestForm(forms.ModelForm):
    """Form for HpcUserChangeRequest."""

    class Meta:
        model = HpcUserChangeRequest
        fields = [
            "expiration",
            "comment",
        ]

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)

        if not user.is_hpcadmin:
            self.fields["expiration"].initial = datetime(
                year=timezone.now().year + 1, month=1, day=31
            )
            self.fields["expiration"].help_text = (
                "Default expiration date is fixed to end of the current year with one month grace "
                "period. "
            )
        else:
            self.fields["expiration"].widget = forms.HiddenInput()
            self.fields["comment"].required = True

        # Some cosmetics
        self.fields["expiration"].widget.attrs["class"] = "form-control"
        self.fields["comment"].widget.attrs["class"] = "form-control"
        self.fields["comment"].widget.attrs["rows"] = 3


class HpcProjectCreateRequestForm(forms.ModelForm):
    """Form for HpcProjectCreateRequest."""

    class Meta:
        model = HpcProjectCreateRequest
        fields = [
            "name_requested",
            "members",
            "delegate",
            "description",
            "comment",
            "resources_requested",
            "expiration",
            "description",
        ]

    def __init__(self, *args, user=None, group=None, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs["instance"]

        self.fields["resources_requested"].widget = forms.HiddenInput()
        self.fields["delegate"].choices = [("", "Select Delegate ...")]

        if instance:
            self.fields["members"].choices = [
                build_option(member) for member in instance.members.all()
            ]
            self.fields["members"].initial = instance.members.all()
            self.fields["delegate"].choices += [
                build_option(member)
                for member in instance.members.all()
                if not member == instance.group.owner
            ]
        else:
            name = "{} {} ({}, AG {})".format(
                group.owner.user.first_name,
                group.owner.user.last_name,
                group.owner.username,
                group.name,
            )
            self.fields["members"].choices = [(str(group.owner.id), name)]
            self.fields["members"].initial = [group.owner.id]

        self.fields["members"].widget.attrs["class"] = "d-none"
        self.fields["delegate"].widget.attrs["class"] = "form-select"

        if not user.is_hpcadmin:
            self.fields["expiration"].disabled = True
            self.fields["expiration"].initial = datetime(
                year=timezone.now().year + 1, month=1, day=31
            )
            self.fields["expiration"].help_text = (
                "Default expiration date is fixed to end of the current year with one month grace "
                "period. It can be extended on request."
            )

            # Add fields for storage. Will be merged into resources_requested field.
            self.fields["tier1_scratch"] = forms.IntegerField(
                required=True,
                help_text=(
                    "Amount of scratch storage on the fast primary ('tier 1') storage that can be "
                    "used with parallel access for computation."
                ),
                label="Fast Active Storage (Scratch) [TB]",
            )
            self.fields["tier1_scratch"].initial = get_project_resource("tier1_scratch", instance)
            self.fields["tier1_scratch"].widget.attrs["class"] = "form-control mergeToJson"

            self.fields["tier1_work"] = forms.IntegerField(
                required=True,
                help_text=(
                    "Amount of work storage on the fast primary ('tier 1') storage that can be "
                    "used with parallel access for computation."
                ),
                label="Fast Active Storage (Work) [TB]",
            )
            self.fields["tier1_work"].initial = get_project_resource("tier1_work", instance)
            self.fields["tier1_work"].widget.attrs["class"] = "form-control mergeToJson"

            self.fields["tier2_unmirrored"] = forms.IntegerField(
                required=True,
                help_text=(
                    "Amount of storage on the slower ('tier 2') storage that is meant for "
                    "long-term storage. This storage is not mirrored and should be used for data "
                    "that can be reconstructed from other sources. Alternatively, you can use your "
                    "group storage at Charite or MDC."
                ),
                label="Long-Term Storage (Unmirrored) [TB]",
            )
            self.fields["tier2_unmirrored"].initial = get_project_resource(
                "tier2_unmirrored", instance
            )
            self.fields["tier2_unmirrored"].widget.attrs["class"] = "form-control mergeToJson"

            self.fields["tier2_mirrored"] = forms.IntegerField(
                required=True,
                help_text=(
                    "Amount of storage on the slower ('tier 2') storage that is meant for "
                    "long-term storage. This storage is mirrored and should be used for data that "
                    "cannot be reconstructed from other sources. Alternatively, you can use your "
                    "group storage at Charite or MDC."
                ),
                label="Long-Term Storage (Mirrored) [TB]",
            )
            self.fields["tier2_mirrored"].initial = get_project_resource("tier2_mirrored", instance)
            self.fields["tier2_mirrored"].widget.attrs["class"] = "form-control mergeToJson"

        else:
            self.fields["name_requested"].widget = forms.HiddenInput()
            self.fields["description"].widget = forms.HiddenInput()
            self.fields["expiration"].widget = forms.HiddenInput()
            self.fields["comment"].required = True

        # Some cosmetics
        self.fields["name_requested"].widget.attrs["class"] = "form-control"
        self.fields["name_requested"].label = "Name"
        self.fields["description"].widget.attrs["class"] = "form-control"
        self.fields["expiration"].widget.attrs["class"] = "form-control"
        self.fields["comment"].widget.attrs["class"] = "form-control"
        self.fields["comment"].widget.attrs["rows"] = 3

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("name_requested")

        if not name:
            return

        if not re.match(RE_NAME_CORE, name):
            self.add_error(
                "name_requested",
                (
                    "The project name must be lowercase, alphanumeric including hyphens (-), not "
                    "starting with a number or a hyphen or ending with a hyphen."
                ),
            )
            return

        if HpcProject.objects.filter(name=name).exists():
            self.add_error("name_requested", "A project with this name already exists.")
            return

        return cleaned_data


class HpcProjectChangeRequestForm(forms.ModelForm):
    """Form for HpcProjectChangeRequest."""

    class Meta:
        model = HpcProjectChangeRequest
        fields = [
            "members",
            "description",
            "delegate",
            "comment",
            "resources_requested",
            "expiration",
            "description",
        ]

    def __init__(self, *args, user=None, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs["instance"]

        self.fields["resources_requested"].widget = forms.HiddenInput()
        self.fields["delegate"].choices = [("", "Select Delegate ...")]

        if instance:
            self.fields["members"].choices = [
                build_option(member) for member in instance.members.all()
            ]
            self.fields["members"].initial = instance.members.all()
            self.fields["delegate"].choices += [
                build_option(member)
                for member in instance.members.all()
                if not member == instance.project.group.owner
            ]
        elif project:
            self.fields["resources_requested"].initial = project.resources_requested
            self.fields["description"].initial = project.description

            self.fields["members"].choices = [
                build_option(member) for member in project.members.all().order_by("user__name")
            ]
            self.fields["members"].initial = project.members.all()
            self.fields["delegate"].choices += [
                build_option(member)
                for member in project.members.all()
                if not member == project.group.owner
            ]
            self.fields["delegate"].initial = project.delegate

        self.fields["members"].widget.attrs["class"] = "d-none"
        self.fields["delegate"].widget.attrs["class"] = "form-select"

        if not user.is_hpcadmin:
            if project.delegate == user.hpcuser_user.first():
                self.fields["delegate"].widget = forms.HiddenInput()

            self.fields["expiration"].initial = datetime(
                year=timezone.now().year + 1, month=1, day=31
            )
            self.fields["expiration"].help_text = (
                "Default expiration date is fixed to end of the current year with one month grace "
                "period."
            )
            # Exclude users from member selection that have no User associated
            self.fields["members_dropdown"] = forms.ModelChoiceField(
                queryset=self.fields["members"]
                .queryset.filter(status="ACTIVE")
                .exclude(user__isnull=True)
                .order_by("user__last_name"),
                label="Select Members",
                help_text="Select members one by one and click add",
                required=False,
            )
            self.fields["members_dropdown"].widget.attrs["class"] = "form-control"

            # Add fields for storage. Will be merged into resources_requested field.
            self.fields["tier1_scratch"] = forms.IntegerField(
                required=True,
                help_text=(
                    "Amount of scratch storage on the fast primary ('tier 1') storage that can be "
                    "used with parallel access for computation."
                ),
                label="Fast Active Storage (Scratch) [TB]",
            )
            self.fields["tier1_scratch"].initial = get_project_resource(
                "tier1_scratch", instance, project
            )
            self.fields["tier1_scratch"].widget.attrs["class"] = "form-control mergeToJson"

            self.fields["tier1_work"] = forms.IntegerField(
                required=True,
                help_text=(
                    "Amount of work storage on the fast primary ('tier 1') storage that can be "
                    "used with parallel access for computation."
                ),
                label="Fast Active Storage (Work) [TB]",
            )
            self.fields["tier1_work"].initial = get_project_resource(
                "tier1_work", instance, project
            )
            self.fields["tier1_work"].widget.attrs["class"] = "form-control mergeToJson"

            self.fields["tier2_unmirrored"] = forms.IntegerField(
                required=True,
                help_text=(
                    "Amount of storage on the slower ('tier 2') storage that is meant for "
                    "long-term storage. This storage is not mirrored and should be used for data "
                    "that can be reconstructed from other sources. Alternatively, you can use your "
                    "group storage at Charite or MDC."
                ),
                label="Long-Term Storage (Unmirrored) [TB]",
            )
            self.fields["tier2_unmirrored"].initial = get_project_resource(
                "tier2_unmirrored", instance, project
            )
            self.fields["tier2_unmirrored"].widget.attrs["class"] = "form-control mergeToJson"

            self.fields["tier2_mirrored"] = forms.IntegerField(
                required=True,
                help_text=(
                    "Amount of storage on the slower ('tier 2') storage that is meant for "
                    "long-term storage. This storage is mirrored and should be used for data that "
                    "cannot be reconstructed from other sources. Alternatively, you can use your "
                    "group storage at Charite or MDC."
                ),
                label="Long-Term Storage (Mirrored) [TB]",
            )
            self.fields["tier2_mirrored"].initial = get_project_resource(
                "tier2_mirrored", instance, project
            )
            self.fields["tier2_mirrored"].widget.attrs["class"] = "form-control mergeToJson"

        else:
            self.fields["delegate"].widget = forms.HiddenInput()
            self.fields["description"].widget = forms.HiddenInput()
            self.fields["expiration"].widget = forms.HiddenInput()
            self.fields["comment"].required = True

        # Some cosmetics
        self.fields["description"].widget.attrs["class"] = "form-control"
        self.fields["expiration"].widget.attrs["class"] = "form-control"
        self.fields["delegate"].widget.attrs["class"] = "form-control"
        self.fields["comment"].widget.attrs["class"] = "form-control"
        self.fields["comment"].widget.attrs["rows"] = 3


class UserSelectForm(forms.Form):
    """Form providing a selector for users from a group."""

    def __init__(self, group, *args, **kwargs):
        super().__init__(*args, **kwargs)

        choices = [
            (
                reverse("usersec:hpcuserchangerequest-create", kwargs={"hpcuser": user.uuid}),
                str(user),
            )
            for user in group.hpcuser.all()
        ]

        self.fields["members"] = forms.ChoiceField(choices=choices)
        self.fields["members"].widget.attrs["class"] = "form-select"


class ProjectSelectForm(forms.Form):
    """Form providing a selector for projects from a group."""

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)

        projects = user.hpcproject_delegate.all()
        group = user.primary_group

        if rules.test_rule("usersec.is_group_manager", user.user, group):
            projects |= group.hpcprojects.all()

        choices = [
            (
                reverse(
                    "usersec:hpcprojectchangerequest-create", kwargs={"hpcproject": project.uuid}
                ),
                str(project),
            )
            for project in projects.order_by("name").distinct()
        ]

        self.fields["projects"] = forms.ChoiceField(choices=choices)

        if not choices:
            self.fields["projects"].disabled = True

        self.fields["projects"].widget.attrs["class"] = "form-select"
