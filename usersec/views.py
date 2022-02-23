from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView


class HomeView(LoginRequiredMixin, TemplateView):
    """Home view"""

    template_name = "usersec/home.html"
