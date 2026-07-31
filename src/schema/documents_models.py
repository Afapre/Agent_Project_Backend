from pydantic import BaseModel, Field

class FolderDirectoryRequest(BaseModel):
    folder_directory: str = Field(..., description="Path of folder with documents to be uploaded")

class FileRequest(BaseModel):
    file_path: str = Field(..., description="File path of single document to be uploaded")