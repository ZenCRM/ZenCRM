from ..extensions import ma
from ..models.contact import Contact

class ContactSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Contact
        load_instance = True
