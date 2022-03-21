import rules
from django.contrib import messages

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseRedirect, Http404, HttpResponseNotFound
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView, FormView, CreateView, DetailView
from rules.contrib.views import PermissionRequiredMixin

from usersec.forms import HpcGroupCreateRequestForm
from usersec.models import HpcGroupCreateRequest


MSG_NO_AUTH = "User not authorized for requested action"
MSG_NO_AUTH_LOGIN = MSG_NO_AUTH + ", please log in"


class HpcPermissionMixin(LoginRequiredMixin, PermissionRequiredMixin):
    """Customized required login and permission mixin"""

    def handle_no_permission(self):
        """Override to redirect user"""
        if self.request.user.is_authenticated:
            messages.error(self.request, MSG_NO_AUTH)
            return redirect(reverse("home"))

        else:
            messages.error(self.request, MSG_NO_AUTH_LOGIN)
            return redirect_to_login(self.request.get_full_path())


class HomeView(LoginRequiredMixin, TemplateView):
    """Home view"""

    template_name = "usersec/home.html"

    def get(self, request, *args, **kwargs):
        if rules.test_rule("is_cluster_user", request.user):
            return redirect(reverse("usersec:dummy"))

        elif rules.test_rule("has_pending_group_request", request.user):
            return redirect(
                reverse(
                    "usersec:pending-group-request",
                    kwargs={
                        "hpcgrouprequest": request.user.hpcgroupcreaterequest_requester.first().uuid
                    },
                )
            )

        return redirect(reverse("usersec:orphan-user"))


class OrphanUserView(HpcPermissionMixin, CreateView):
    """Orphan user view"""

    template_name = "usersec/orphan.html"
    form_class = HpcGroupCreateRequestForm
    permission_required = "usersec.create_hpcgroupcreaterequest"

    def get_success_url(self, uuid):
        return reverse("usersec:pending-group-request", kwargs={"hpcgrouprequest": uuid})

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.requester = self.request.user
        obj = obj.save_with_version()

        if not obj:
            messages.error(self.request, "Couldn't create group request.")
            return HttpResponseRedirect(reverse("usersec:orphan-user"))

        messages.success(self.request, "Group request submitted.")
        return HttpResponseRedirect(self.get_success_url(obj.uuid))


class PendingGroupRequestView(HpcPermissionMixin, DetailView):
    """Pending group request view"""

    template_name = "usersec/pending.html"
    model = HpcGroupCreateRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcgrouprequest"
    permission_required = "usersec.view_hpcgroupcreaterequest"


class DummyView(LoginRequiredMixin, TemplateView):
    template_name = "usersec/dummy.html"
