from django import forms

from usersec.models import HpcGroupCreateRequest


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
            self.fields["comment"].required = True
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
            self.add_error(
                "resources_requested", "Resources must be a dictionary!"
            )
            return

        return cleaned_data
