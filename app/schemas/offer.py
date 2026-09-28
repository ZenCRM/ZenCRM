from ..extensions import ma
from ..models.offer import Offer

class OfferSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Offer
        load_instance = True
