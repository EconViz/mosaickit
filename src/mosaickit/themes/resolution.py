from mosaickit.themes._walk import role_chain
from mosaickit.themes.builtins import PRIMITIVE_DEFAULT
from mosaickit.themes.theme import StyleBundle, Theme


def resolve(theme: Theme, role: str, *, fallback_category: str) -> StyleBundle:
    result = PRIMITIVE_DEFAULT
    for key in reversed(role_chain(role, fallback_category)):
        result = theme.roles.get(key, StyleBundle()).merged_over(result)
    return result
