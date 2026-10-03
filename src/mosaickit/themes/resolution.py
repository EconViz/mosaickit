from collections.abc import Mapping, Sequence

from mosaickit.themes._walk import role_chain
from mosaickit.themes.builtins import PRIMITIVE_DEFAULT
from mosaickit.themes.theme import StyleBundle, Theme


def resolve(
    theme: Theme,
    role: str,
    *,
    fallback_category: str,
    overrides: Sequence[Mapping[str, StyleBundle]] = (),
) -> StyleBundle:
    """Primitive defaults, then the theme, then each override mapping in order."""
    chain = tuple(reversed(role_chain(role, fallback_category)))
    result = theme.defaults.merged_over(PRIMITIVE_DEFAULT)
    for roles in (theme.roles, *overrides):
        for key in chain:
            result = roles.get(key, StyleBundle()).merged_over(result)
    return result
