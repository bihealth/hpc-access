# Create your tasks here
import os

import yaml

from config.celery import app
from usersec.models import HpcProject


@app.task(bind=True)
def export_projects(_self):
    with open("export/projects.yaml", "w") as fh:
        projects = [
            {
                "uuid": str(project.uuid),
                "type": "HpcProject",
                "date_created": str(project.date_created),
                "description": project.description,
                "status": project.status,
                "name": project.name,
                "expiration": str(project.expiration),
                "group": {
                    "name": project.group.name,
                    "owner": project.group.owner.username,
                },
                "members": [member.username for member in project.members.all()],
            }
            for project in HpcProject.objects.all()
        ]
        print(f"Exporting {len(projects)} projects to {os.path.realpath(fh.name)} ...")
        yaml.dump(projects, fh)
