from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views import View
from django.views.generic import TemplateView, FormView


class HomeView(LoginRequiredMixin, TemplateView):
    """Home view"""

    template_name = "usersec/home.html"


# class OrphanUserView(LoginRequiredMixin, FormView):
#     """Orphan user view"""
#
#     template_name = "usersec/orphan.html"


# class SomeView(LoginRequiredMixin, PermissionRequiredMixin, View):
#     template_name = "usersec/some.html"
#     permission_required = "usersec"
