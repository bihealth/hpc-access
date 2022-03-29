from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import (
    DetailView,
    UpdateView,
    DeleteView,
    TemplateView,
)

from usersec.forms import HpcGroupCreateRequestForm
from usersec.models import HpcGroupCreateRequest
from usersec.views import HpcPermissionMixin


class AdminView(HpcPermissionMixin, TemplateView):

    """Admin welcome view."""

    template_name = "adminsec/overview.html"
    permission_required = "adminsec.is_hpcadmin"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add open HpcGroupCreateRequest
        context[
            "hpcgroupcreaterequests"
        ] = HpcGroupCreateRequest.objects.active()

        # TODO: Add other open requests

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
        context["comment_history"] = obj.get_comment_history()
        context["is_denied"] = obj.is_denied()
        context["is_retracted"] = obj.is_retracted()
        context["is_approved"] = obj.is_approved()
        context["is_decided"] = obj.is_decided()
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context["update"] = True
        context["comment_history"] = obj.get_comment_history()
        context["admin"] = True
        return context

    def get_success_url(self):
        return reverse(
            "adminsec:hpcgroupcreaterequest-detail",
            kwargs={"hpcgroupcreaterequest": self.get_object().uuid},
        )

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
            messages.error(self.request, "Couldn't update group request.")
            return HttpResponseRedirect(reverse("adminsec:overview"))

        messages.success(self.request, "Revision requested.")
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
        obj.comment = ""
        obj.editor = self.request.user
        obj.approve_with_version()
        messages.success(self.request, "Request successfully approved.")
        return HttpResponseRedirect(
            reverse(
                "adminsec:hpcgroupcreaterequest-detail",
                kwargs={"hpcgroupcreaterequest": obj.uuid},
            )
        )


class HpcGroupCreateRequestDenyView(HpcPermissionMixin, DeleteView):

    """Pending group request update view."""

    template_name_suffix = "_deny_confirm"
    model = HpcGroupCreateRequest
    slug_field = "uuid"
    slug_url_kwarg = "hpcgroupcreaterequest"
    permission_required = "adminsec.is_hpcadmin"

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.comment = ""
        obj.editor = self.request.user
        obj.deny_with_version()
        messages.success(self.request, "Request successfully denied.")
        return HttpResponseRedirect(
            reverse(
                "adminsec:hpcgroupcreaterequest-detail",
                kwargs={"hpcgroupcreaterequest": obj.uuid},
            )
        )
