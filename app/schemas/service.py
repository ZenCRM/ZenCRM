from ..extensions import ma
from ..models.service import Service

class ServiceSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Service
        load_instance = True
