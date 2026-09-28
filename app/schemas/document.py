from ..extensions import ma
from ..models.document import Document

class DocumentSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Document
        load_instance = True
