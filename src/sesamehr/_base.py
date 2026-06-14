from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class SesameModel(BaseModel):
    """Base for all SDK models.

    The API speaks camelCase; Python attributes are snake_case. The alias
    generator maps between both, `populate_by_name` accepts either on input,
    and `extra="allow"` keeps unknown API fields accessible via `model_extra`
    instead of failing validation.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="allow",
        coerce_numbers_to_str=True,
    )
