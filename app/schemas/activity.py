from ..extensions import ma
from ..models.activity import Activity

class ActivitySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Activity
        load_instance = True
