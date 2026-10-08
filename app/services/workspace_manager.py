from app.models.workspace import Workspace

class WorkspaceManager:
    def __init__(self):
        self.workspaces: dict[str, Workspace] = {}

    def create(self):
        workspace = Workspace()
        self.workspaces[workspace.id] = workspace
        return workspace

    def get(self, workspace_id: str):
        return self.workspaces.get(workspace_id)

    def get_or_create(self, workspace_id=None):
        if workspace_id:
            workspace = self.get(workspace_id)

            if workspace:
                return workspace

        return self.create()

    def update_config(self, workspace_id: str, **values):
        workspace = self.get(workspace_id)

        if not workspace:
            return None

        for key, value in values.items():
            if hasattr(workspace.config, key):
                setattr(workspace.config, key, value)

        return workspace