from django.urls import path

from usersec import views


app_name = "usersec"


urlpatterns = [
    path("orphan/", view=views.OrphanUserView.as_view(), name="orphan-user"),
    path(
        "pending/<uuid:hpcgrouprequest>/",
        view=views.PendingGroupRequestView.as_view(),
        name="pending-group-request",
    ),
    path("dummy/", view=views.DummyView.as_view(), name="dummy"),
]
