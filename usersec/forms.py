from django import forms
from django.conf import settings
from django.utils import timezone
from django.utils.datetime_safe import datetime

from usersec.models import (
    HpcGroupCreateRequest,
    HpcUserCreateRequest,
    HpcProjectCreateRequest,
    HpcGroupChangeRequest,
)


DEFAULT_USER_RESOURCES = {"tier1": "1", "tier2": "0"}
DEFAULT_GROUP_RESOURCES = {"tier1": "1", "tier2": "0"}
DEFAULT_PROJECT_RESOURCES = {"tier1": "1", "tier2": "0"}


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

        # Add fields for storage. Will be merged into resources_requested field.
        if not user.is_hpcadmin:
            self.fields["expiration"].disabled = True
            self.fields["expiration"].initial = datetime(
                year=timezone.now().year + 1, month=1, day=31
            )
            self.fields["expiration"].help_text = (
                "Default expiration date is fixed to end of the current year with one month grace period. "
                "It can be extended on request."
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
            "For the initial group creation request provide some 'proof' that you are a group leader such as linking "
            "to your group website at Charite or MDC."
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
        self.fields["resources_requested"].initial = group.resources_requested
        self.fields["description"].initial = group.description
        self.fields["delegate"].initial = group.delegate

        # Add fields for storage. Will be merged into resources_requested field.
        if not user.is_hpcadmin:
            self.fields["expiration"].initial = datetime(
                year=timezone.now().year + 1, month=1, day=31
            )
            self.fields[
                "expiration"
            ].help_text = "Default expiration date is set to end of the current year with one month grace period."

            # Add fields for storage. Will be merged into resources_requested field.
            self.fields["tier1"] = forms.IntegerField(
                required=True,
                help_text=(
                    "Amount of storage on the fast primary ('tier 1') storage that can be used with parallel access "
                    "for computation."
                ),
                label="Fast Active Storage [TB]",
            )
            self.fields["tier1"].initial = group.resources_requested["tier1"]
            self.fields["tier1"].widget.attrs["class"] = "form-control mergeToJson"

            self.fields["tier2"] = forms.IntegerField(
                required=True,
                help_text=(
                    "Amount of storage on the slower ('tier 2') storage that is meant for long-term storage. "
                    "Alternatively, you can use your group storage at Charite or MDC."
                ),
                label="Long-Term Storage [TB]",
            )
            self.fields["tier2"].initial = group.resources_requested["tier2"]
            self.fields["tier2"].widget.attrs["class"] = "form-control mergeToJson"

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
                "Default expiration date is fixed to end of the current year with one month grace period. "
                "It can be extended on request."
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

        if email_split[1].lower() not in valid_domains:
            self.add_error("email", "No institute email address.")
            return

        return cleaned_data


class HpcProjectCreateRequestForm(forms.ModelForm):
    """Form for HpcProjectCreateRequest."""

    class Meta:
        model = HpcProjectCreateRequest
        fields = [
            "name",
            "members",
            "description",
            "delegate",
            "comment",
            "resources_requested",
            "expiration",
            "description",
        ]

    def __init__(self, *args, user=None, group=None, **kwargs):
        super().__init__(*args, **kwargs)

        if hasattr(self.instance, "group"):
            group = self.instance.group

        # Exclude users from delegate selection that have no User associated
        self.fields["delegate"].queryset = (
            self.fields["delegate"].queryset.exclude(user__isnull=True).exclude(id=group.owner.id)
        )

        self.fields["resources_requested"].widget = forms.HiddenInput()

        if not user.is_hpcadmin:
            self.fields["expiration"].disabled = True
            self.fields["expiration"].initial = datetime(
                year=timezone.now().year + 1, month=1, day=31
            )
            self.fields["expiration"].help_text = (
                "Default expiration date is fixed to end of the current year with one month grace period. "
                "It can be extended on request."
            )

            # Exclude users from member selection that have no User associated
            self.fields["members_dropdown"] = forms.ModelChoiceField(
                queryset=self.fields["members"].queryset.exclude(user__isnull=True),
                label="Select Members",
                help_text="Select members one by one and click add",
                required=False,
            )
            self.fields["members_dropdown"].widget.attrs["class"] = "form-control"

            # Add fields for storage. Will be merged into resources_requested field.
            self.fields["tier1"] = forms.IntegerField(
                required=True,
                help_text=(
                    "Amount of storage on the fast primary ('tier 1') storage that can be used with parallel access "
                    "for computation."
                ),
                label="Fast Active Storage [TB]",
            )
            self.fields["tier1"].initial = DEFAULT_PROJECT_RESOURCES["tier1"]
            self.fields["tier1"].widget.attrs["class"] = "form-control mergeToJson"

            self.fields["tier2"] = forms.IntegerField(
                required=True,
                help_text=(
                    "Amount of storage on the slower ('tier 2') storage that is meant for long-term storage. "
                    "Alternatively, you can use your group storage at Charite or MDC."
                ),
                label="Long-Term Storage [TB]",
            )
            self.fields["tier2"].initial = DEFAULT_PROJECT_RESOURCES["tier2"]
            self.fields["tier2"].widget.attrs["class"] = "form-control mergeToJson"

        else:
            self.fields["delegate"].widget = forms.HiddenInput()
            self.fields["name"].widget = forms.HiddenInput()
            self.fields["description"].widget = forms.HiddenInput()
            self.fields["expiration"].widget = forms.HiddenInput()
            self.fields["comment"].required = True

        # Some cosmetics
        self.fields["name"].widget.attrs["class"] = "form-control"
        self.fields["description"].widget.attrs["class"] = "form-control"
        self.fields["expiration"].widget.attrs["class"] = "form-control"
        self.fields["delegate"].widget.attrs["class"] = "form-control"
        self.fields["comment"].widget.attrs["class"] = "form-control"
        self.fields["comment"].widget.attrs["rows"] = 3

    def clean(self):
        cleaned_data = super().clean()

        return cleaned_data
