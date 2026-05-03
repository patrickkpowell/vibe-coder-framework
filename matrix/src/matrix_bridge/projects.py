from __future__ import annotations

import os
from dataclasses import dataclass, field

import yaml


class ManifestError(Exception):
    pass


@dataclass
class ProjectManifest:
    project_id: str
    name: str
    root_path: str
    architecture_docs: list[str]
    specs: list[str]
    skills: list[str]
    default_branch: str
    matrix_room_id: str | None
    notification_policy: str
    allowed_tools: list[str]

    def existing_docs(self) -> list[str]:
        return [d for d in self.architecture_docs if os.path.exists(os.path.join(self.root_path, d))]

    def existing_specs(self) -> list[str]:
        return [s for s in self.specs if os.path.exists(os.path.join(self.root_path, s))]


def _canonical_id(project_id: str) -> str:
    """Accept '1', '001', 'project-001' — always return '001' form."""
    pid = project_id.lower().removeprefix("project-").lstrip("0") or "0"
    try:
        return f"{int(pid):03d}"
    except ValueError:
        return project_id


def load_manifest(projects_dir: str, project_id: str) -> ProjectManifest:
    pid = _canonical_id(project_id)
    path = os.path.join(projects_dir, f"{pid}.yaml")
    if not os.path.exists(path):
        raise ManifestError(
            f"No manifest found for project {pid!r}.\n"
            f"Expected: {path}"
        )
    with open(path) as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        raise ManifestError(f"Manifest at {path} is not a YAML mapping.")

    missing = [k for k in ("project_id", "name", "root_path") if not data.get(k)]
    if missing:
        raise ManifestError(f"Manifest {path} is missing required keys: {missing}")

    return ProjectManifest(
        project_id=str(data["project_id"]),
        name=str(data["name"]),
        root_path=str(data["root_path"]),
        architecture_docs=data.get("architecture_docs") or [],
        specs=data.get("specs") or [],
        skills=data.get("skills") or [],
        default_branch=str(data.get("default_branch", "main")),
        matrix_room_id=data.get("matrix_room_id"),
        notification_policy=str(data.get("notification_policy", "matrix-active-only")),
        allowed_tools=data.get("allowed_tools") or [],
    )


def list_manifests(projects_dir: str) -> list[ProjectManifest]:
    if not os.path.isdir(projects_dir):
        return []
    manifests = []
    for fname in sorted(os.listdir(projects_dir)):
        if fname.endswith(".yaml"):
            try:
                manifests.append(load_manifest(projects_dir, fname[:-5]))
            except ManifestError:
                pass
    return manifests
