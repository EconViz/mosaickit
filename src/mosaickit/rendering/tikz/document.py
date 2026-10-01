"""TikZ wrappers and safe plain-text labels."""


def escape_text(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def assemble(body: str, *, fragment: bool = False) -> str:
    picture = "\\begin{tikzpicture}\n" + body + "\n\\end{tikzpicture}\n"
    if fragment:
        return picture
    return (
        "\\documentclass[tikz,border=2pt]{standalone}\n"
        "\\usepackage{amsmath}\n"
        "\\usetikzlibrary{arrows.meta,patterns}\n"
        "\\usepgflibrary{plotmarks}\n"
        "\\begin{document}\n" + picture + "\\end{document}\n"
    )
