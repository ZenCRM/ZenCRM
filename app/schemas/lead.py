from ..extensions import ma
from ..models.lead import Lead


class LeadSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Lead
        load_instance = True
        include_fk = True

    id = ma.auto_field()
    title = ma.auto_field()
    client_id = ma.auto_field()
    assignee_id = ma.auto_field()
    value = ma.auto_field()
    stage = ma.auto_field()
    source = ma.auto_field()
    probability = ma.auto_field()
    expected_close_date = ma.auto_field()
    notes = ma.auto_field()
    converted_to_client_id = ma.auto_field()
    created_at = ma.auto_field()
