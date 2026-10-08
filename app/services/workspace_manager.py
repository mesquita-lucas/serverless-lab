import time

from app.models.workspace import Workspace

class WorkspaceManager:
    def __init__(
        self,
        expiration_seconds=1800,
    ):
        self.workspaces: dict[
            str,
            Workspace,
        ] = {}

        self.expiration_seconds = (
            expiration_seconds
        )

    def create(self):
        workspace = Workspace()

        self.workspaces[
            workspace.id
        ] = workspace

        return workspace

    def get(
        self,
        workspace_id: str,
        touch=True,
    ):
        workspace = self.workspaces.get(
            workspace_id
        )

        if workspace and touch:
            workspace.touch()

        return workspace

    def get_or_create(
        self,
        workspace_id=None,
    ):
        if workspace_id:
            workspace = self.get(
                workspace_id
            )

            if workspace:
                return workspace

        return self.create()

    def update_config(
        self,
        workspace_id: str,
        **values,
    ):
        workspace = self.get(
            workspace_id
        )

        if not workspace:
            return None

        for key, value in values.items():
            if hasattr(
                workspace.config,
                key,
            ):
                setattr(
                    workspace.config,
                    key,
                    value,
                )

        workspace.touch()

        return workspace

    def expired_ids(self):
        now = time.monotonic()

        return [
            workspace_id
            for workspace_id, workspace
            in self.workspaces.items()
            if (
                now - workspace.last_activity
                > self.expiration_seconds
            )
        ]

    def remove(
        self,
        workspace_id: str,
    ):
        return self.workspaces.pop(
            workspace_id,
            None,
        )