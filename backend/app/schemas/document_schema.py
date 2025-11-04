from pydantic import BaseModel
from datetime import datetime

class DocumentResponse(BaseModel):
    id: int
    file_name: str
    upload_date: datetime
    parsing_status: str

    class Config:
        orm_mode = True
