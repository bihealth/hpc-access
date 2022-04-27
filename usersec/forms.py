from datetime import timedelta

from django import forms
from django.conf import settings
from django.utils import timezone

from usersec.models import (
    HpcGroupCreateRequest,
    HpcUserCreateRequest,
    HpcProjectCreateRequest,
)


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

        self.fields["expiration"].widget = forms.HiddenInput()
        self.fields["resources_requested"].widget = forms.HiddenInput()

        # Add fields for storage. Will be merged into resources_requested field.
        if not user.is_hpcadmin:
            self.fields["expiration"].initial = timezone.now() + timedelta(weeks=52)

            self.fields["tier1"] = forms.IntegerField(
                required=True, help_text="Default storage in TB"
            )
            self.fields["tier1"].initial = 1
            self.fields["tier1"].widget.attrs["class"] = "form-control mergeToJson"

            self.fields["tier2"] = forms.IntegerField(
                required=True, help_text="Long-term storage in TB"
            )
            self.fields["tier2"].initial = 1
            self.fields["tier2"].widget.attrs["class"] = "form-control mergeToJson"

        else:
            self.fields["description"].widget = forms.HiddenInput()
            self.fields["comment"].required = True

        # Some cosmetics
        self.fields["description"].widget.attrs["class"] = "form-control"
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

        self.fields["expiration"].widget = forms.HiddenInput()
        self.fields["resources_requested"].widget = forms.HiddenInput()

        if not user.is_hpcadmin:
            self.fields["expiration"].initial = timezone.now() + timedelta(weeks=52)

            # Add fields for storage. Will be merged into resources_requested field.
            self.fields["tier1"] = forms.IntegerField(
                required=True, help_text="Default storage in TB"
            )
            self.fields["tier1"].initial = 1
            self.fields["tier1"].widget = forms.HiddenInput()
            self.fields["tier1"].widget.attrs["class"] = "form-control mergeToJson"

            self.fields["tier2"] = forms.IntegerField(
                required=True, help_text="Long-term storage in TB"
            )
            self.fields["tier2"].initial = 1
            self.fields["tier2"].widget = forms.HiddenInput()
            self.fields["tier2"].widget.attrs["class"] = "form-control mergeToJson"

        else:
            self.fields["email"].widget = forms.HiddenInput()
            self.fields["comment"].required = True

        # Some cosmetics
        self.fields["email"].widget.attrs["class"] = "form-control"
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

        self.fields["expiration"].widget = forms.HiddenInput()
        self.fields["resources_requested"].widget = forms.HiddenInput()

        if not user.is_hpcadmin:
            self.fields["expiration"].initial = timezone.now() + timedelta(weeks=52)

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
                required=True, help_text="Default storage in TB"
            )
            self.fields["tier1"].initial = 1
            self.fields["tier1"].widget.attrs["class"] = "form-control mergeToJson"

            self.fields["tier2"] = forms.IntegerField(
                required=True, help_text="Long-term storage in TB"
            )
            self.fields["tier2"].initial = 1
            self.fields["tier2"].widget.attrs["class"] = "form-control mergeToJson"

        else:
            self.fields["delegate"].widget = forms.HiddenInput()
            self.fields["name"].widget = forms.HiddenInput()
            self.fields["description"].widget = forms.HiddenInput()
            self.fields["comment"].required = True

        # Some cosmetics
        self.fields["name"].widget.attrs["class"] = "form-control"
        self.fields["description"].widget.attrs["class"] = "form-control"
        self.fields["delegate"].widget.attrs["class"] = "form-control"
        self.fields["comment"].widget.attrs["class"] = "form-control"
        self.fields["comment"].widget.attrs["rows"] = 3

    def clean(self):
        cleaned_data = super().clean()

        return cleaned_data
