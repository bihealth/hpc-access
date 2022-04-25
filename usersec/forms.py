from django import forms
from django.conf import settings

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

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.is_hpcadmin:
            self.fields["resources_requested"].widget = forms.HiddenInput()
            self.fields["expiration"].widget = forms.HiddenInput()
            self.fields["description"].widget = forms.HiddenInput()

    def clean(self):
        """Override clean to extend the checks."""
        cleaned_data = super().clean()
        resources = cleaned_data.get("resources_requested", {})

        if not resources:
            return

        # Resources requested must be a dict
        if not isinstance(resources, dict):
            self.add_error("resources_requested", "Resources must be a dictionary!")
            return

        return cleaned_data


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

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.is_hpcadmin:
            self.fields["resources_requested"].widget = forms.HiddenInput()
            self.fields["expiration"].widget = forms.HiddenInput()
            self.fields["email"].widget = forms.HiddenInput()

    def clean(self):
        """Override clean to extend the checks."""
        cleaned_data = super().clean()
        resources = cleaned_data.get("resources_requested", {})
        email = cleaned_data.get("email")

        if not (resources and email):
            return

        # Resources requested must be a dict
        if not isinstance(resources, dict):
            self.add_error("resources_requested", "Resources must be a dictionary!")
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
            "resources_requested",
            "expiration",
            "delegate",
            "name",
            "comment",
            "members",
            "description",
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Exclude members that have no User associated
        self.fields["members"].queryset = self.fields["members"].queryset.exclude(user__isnull=True)

        if user and user.is_hpcadmin:
            self.fields["resources_requested"].widget = forms.HiddenInput()
            self.fields["expiration"].widget = forms.HiddenInput()
            self.fields["delegate"].widget = forms.HiddenInput()
            self.fields["name"].widget = forms.HiddenInput()
            self.fields["members"].widget = forms.MultipleHiddenInput()
            self.fields["description"].widget = forms.HiddenInput()

    def clean(self):
        """Override clean to extend the checks."""
        cleaned_data = super().clean()
        resources = cleaned_data.get("resources_requested", {})

        if not resources:
            return

        # Resources requested must be a dict
        if not isinstance(resources, dict):
            self.add_error("resources_requested", "Resources must be a dictionary!")
            return

        return cleaned_data
