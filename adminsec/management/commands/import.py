"""Command for importing data from a json file."""

from collections.abc import Generator
from contextlib import contextmanager

from django.contrib import auth
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import make_aware

from usersec.models import HpcGroup, HpcProject, HpcUser

from .models import HpcaccessState

User = auth.get_user_model()


class Rollback(Exception):
    pass


@contextmanager
def rollback(_self) -> Generator[None, None, None]:
    try:
        with transaction.atomic():
            yield
            raise Rollback()
    except Rollback:
        _self.stderr.write("Dry run succeeded. Use `--write` to save to database.")
        pass


SUFFIX_MAPPING = {
    "c": "@CHARITE",
    "m": "@MDC-BERLIN",
}


class Command(BaseCommand):
    help = "Import HPC objects from a json file."

    def add_arguments(self, parser):
        parser.add_argument("json", type=str)
        parser.add_argument("--write", action="store_true")

    def handle(self, *args, **options):
        worker_user = User.objects.get(username="hpc-worker")
        context = transaction.atomic() if options["write"] else rollback(self)
        try:
            with context, open(options["json"], "r") as jsonfile:
                data = HpcaccessState.model_validate_json(jsonfile.read())
                for group_uuid, group_data in data.hpc_groups.items():
                    hpcgroup = HpcGroup(
                        uuid=group_uuid,
                        name=group_data.name,
                        description=group_data.description,
                        creator=worker_user,
                        status=group_data.status.name,
                        gid=group_data.gid,
                        folder=group_data.folder,
                        resources_requested={
                            "tier1_scratch": group_data.resources_requested.tier1_scratch,
                            "tier1_work": group_data.resources_requested.tier1_scratch,
                            "tier2_mirrored": group_data.resources_requested.tier1_scratch,
                            "tier2_unmirrored": group_data.resources_requested.tier1_scratch,
                        },
                        resources_used={
                            "tier1_scratch": group_data.resources_used.tier1_scratch,
                            "tier1_work": group_data.resources_used.tier1_scratch,
                            "tier2_mirrored": group_data.resources_used.tier1_scratch,
                            "tier2_unmirrored": group_data.resources_used.tier1_scratch,
                        },
                        expiration=make_aware(group_data.expiration),
                    )
                    hpcgroup.save_with_version()

                for user_uuid, user_data in data.hpc_users.items():
                    ldap_user, suffix = user_data.username.split("_")
                    if user_data.primary_group:
                        hpcgroup = HpcGroup.objects.filter(uuid=user_data.primary_group)
                        if not hpcgroup:
                            self.stderr.write(
                                f"Primary group {user_data.primary_group} of user "
                                f"{user_data.username} not found"
                            )
                            continue
                        hpcgroup = hpcgroup.first()
                    else:
                        hpcgroup = None

                    user = User.objects.create(
                        first_name=user_data.first_name.strip(),
                        last_name=user_data.last_name.strip(),
                        name=user_data.full_name.strip(),
                        email=user_data.email,
                        is_staff=False,
                        is_superuser=False,
                        is_hpcadmin=False,
                        phone=user_data.phone_number,
                        uid=user_data.uid,
                        username=f"{ldap_user}{SUFFIX_MAPPING[suffix]}",
                    )
                    hpcuser = HpcUser(
                        uuid=user_uuid,
                        user=user,
                        resources_requested={
                            "tier1_home": user_data.resources_requested.tier1_home,
                        },
                        resources_used={
                            "tier1_home": user_data.resources_used.tier1_home,
                        },
                        creator=worker_user,
                        status=user_data.status.name,
                        home_directory=user_data.home_directory,
                        primary_group=hpcgroup,
                        expiration=make_aware(user_data.expiration),
                        login_shell=user_data.login_shell,
                        username=user_data.username,
                    )
                    hpcuser.save_with_version()

                for group_uuid, group_data in data.hpc_groups.items():
                    hpcgroup = HpcGroup.objects.filter(uuid=group_uuid)
                    if not hpcgroup:
                        self.stderr.write(f"Group {group_uuid} not found")
                        continue
                    hpcgroup = hpcgroup.first()
                    owner = HpcUser.objects.filter(uuid=group_data.owner)
                    if not owner:
                        self.stderr.write(
                            f"Owner {group_data.owner} of group {group_data.name} not found"
                        )
                        continue
                    hpcgroup.owner = owner.first()
                    if group_data.delegate:
                        delegate = HpcUser.objects.filter(uuid=group_data.delegate)
                        if not delegate:
                            self.stderr.write(
                                f"Delegate {group_data.delegate} of group "
                                f"{group_data.name} not found"
                            )
                            continue
                        hpcgroup.delegate = delegate.first()
                    hpcgroup.save_with_version()

                for project_uuid, project_data in data.hpc_projects.items():
                    hpcgroup = HpcGroup.objects.filter(uuid=project_data.group)
                    if not hpcgroup:
                        self.stderr.write(
                            f"Owning group {project_data.group} of project "
                            f"{project_data.name} not found"
                        )
                        continue
                    hpcgroup = hpcgroup.first()
                    delegate = HpcUser.objects.filter(uuid=project_data.delegate)
                    delegate = delegate.first() if delegate else None
                    hpcproject = HpcProject(
                        uuid=project_uuid,
                        name=project_data.name,
                        gid=project_data.gid,
                        folder=project_data.folder,
                        status=project_data.status.name,
                        creator=worker_user,
                        group=hpcgroup,
                        delegate=delegate,
                        resources_requested={
                            "tier1_scratch": project_data.resources_requested.tier1_scratch,
                            "tier1_work": project_data.resources_requested.tier1_scratch,
                            "tier2_mirrored": project_data.resources_requested.tier1_scratch,
                            "tier2_unmirrored": project_data.resources_requested.tier1_scratch,
                        },
                        resources_used={
                            "tier1_scratch": project_data.resources_used.tier1_scratch,
                            "tier1_work": project_data.resources_used.tier1_scratch,
                            "tier2_mirrored": project_data.resources_used.tier1_scratch,
                            "tier2_unmirrored": project_data.resources_used.tier1_scratch,
                        },
                        expiration=make_aware(project_data.expiration),
                    )
                    hpcproject.save_with_version()
                    for member_uuid in project_data.members:
                        member = HpcUser.objects.filter(uuid=member_uuid)
                        if not member:
                            self.stderr.write(
                                f"Member {member_uuid} of project {project_data.name} not found"
                            )
                            continue
                        hpcproject.members.add(member.first())
                        hpcproject.version_history.last().members.add(member.first())

        except Rollback:
            pass
