from ..extensions import ma
from ..models.template import Template

class TemplateSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Template
        load_instance = True
