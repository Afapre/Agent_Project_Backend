from pydantic import BaseModel, Field

class FolderDirectoryRequest(BaseModel):
    folder_directory: str = Field(..., description="File path of docments to be uploaded")