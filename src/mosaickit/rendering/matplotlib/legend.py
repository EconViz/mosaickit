from mosaickit.errors import RenderError


def build_legend(ax, resolved, handles):
    layer, style = resolved.layer, resolved.style.legend
    if not style.visible:
        return None
    ids = layer.entries or tuple(handles)
    missing = set(ids) - handles.keys()
    if missing:
        raise RenderError(f"Legend references missing or unlabelled layers: {sorted(missing)}")
    selected = [handles[key] for key in ids]
    if not selected:
        return None
    return ax.legend(
        handles=selected,
        labels=[handle.get_label() for handle in selected],
        loc=style.location,
        frameon=style.frame,
        fontsize=style.size,
    )
