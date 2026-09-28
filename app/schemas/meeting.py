from ..extensions import ma
from ..models.meeting import Meeting

class MeetingSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Meeting
        load_instance = True
        include_fk = True
