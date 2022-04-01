from django import forms

from usersec.models import HpcGroupCreateRequest, HpcUserCreateRequest


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

        if not len(email_split) == 2:
            self.add_error("email", "Not a valid email address.")
            return

        if email_split[1].lower() not in ("charite.de", "bih-charite.de", "mdc-berlin.de"):
            self.add_error("email", "No institute email address.")
            return

        return cleaned_data
