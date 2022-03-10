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
            "delegate_email",
            "member_emails",
        ]
