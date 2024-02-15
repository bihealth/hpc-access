from django.contrib.auth.models import AbstractUser
from django.db.models import BooleanField, CharField, EmailField, IntegerField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Default custom user model for hpcaccess.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    #: First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, null=True, max_length=255)
    is_hpcadmin = BooleanField(
        _("HPC admin status"),
        default=False,
        help_text=_("Designates whether the user is an HPC admin."),
    )
    phone = CharField(_("Phone number of User"), blank=True, null=True, max_length=32)
    email = EmailField(_("email address"), blank=True, null=True)
    uid = IntegerField(_("UID of User"), blank=True, null=True)

    def get_absolute_url(self):
        """Get url for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})
