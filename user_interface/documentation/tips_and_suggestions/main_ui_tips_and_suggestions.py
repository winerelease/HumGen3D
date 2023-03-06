# Copyright (c) 2022 Oliver J. Post & Alexander Lashko - GNU GPL V3.0, see LICENSE
from enum import Enum

from HumGen3D.user_interface.documentation.tips_and_suggestions.tip_baseclasses import (
    Tip,
    URLOperator,
)

# String enum of possible active sections
class ActiveSection(str, Enum):
    """Enum of possible active sections."""

    BODY = "body"
    AGE = "age"
    FACE = "face"
    HEIGHT = "height"
    SKIN = "skin"
    HAIR = "hair"
    CLOTHING = "clothing"
    POSE = "pose"
    EXPRESSION = "expression"


CLOTHING_MATERIAL_MENU_TIP = Tip(
    title="Clothing Materials",
    text="""By selecting a clothing object, the Human Generator
interface will change to the clothing material menu.

This menu allows you to change the colors of the clothing
and also add patterns to it.""",
)


def get_main_ui_tips_from_context(context, sett, human):
    active_tab = sett.ui.phase

    if active_tab == ActiveSection.CLOTHING and human.clothing.outfit.objects:
        yield CLOTHING_MATERIAL_MENU_TIP
