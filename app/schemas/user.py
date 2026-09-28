from ..extensions import ma
from ..models.user import User


class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True
        include_fk = True

    id = ma.auto_field()
    email = ma.auto_field()
    first_name = ma.auto_field()
    last_name = ma.auto_field()
    role = ma.auto_field()
    is_active = ma.auto_field()
    avatar_url = ma.auto_field()
    created_at = ma.auto_field()
    # password_hash NIE jest tu umyślnie – nie chcemy go w API
