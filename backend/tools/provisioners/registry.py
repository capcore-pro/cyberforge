from __future__ import annotations

from tools.managed_project import ManagedProjectProvisioner
from tools.provisioners.application_web import ApplicationWebProvisioner
from tools.provisioners.extension_navigateur import ExtensionNavigateurProvisioner
from tools.provisioners.vitrine_next import VitrineNextProvisioner


def get_provisioners() -> list[ManagedProjectProvisioner]:
    # V1: only vitrine_next. V2+: append other project types here.
    return [VitrineNextProvisioner(), ApplicationWebProvisioner(), ExtensionNavigateurProvisioner()]


def get_provisioner_for_type(project_type: str) -> ManagedProjectProvisioner | None:
    for p in get_provisioners():
        if p.project_type == project_type:
            return p
    return None

