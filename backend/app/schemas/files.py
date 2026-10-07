from pydantic import BaseModel


class FileIngestRequest(BaseModel):
    filename: str
    content_base64: str
    # Owner of the file: documents are only searchable within this session.
    session_id: str
    user_name: str | None = None


class FileIngestResponse(BaseModel):
    kind: str  # "document" | "spreadsheet"
    filename: str
    chunks: int
