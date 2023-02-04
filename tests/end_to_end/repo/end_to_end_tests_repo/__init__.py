def f(a="", b="", c="", d=""):
    elements = []
    if a:
        elements.append(a)

    if b:
        elements.append(b)

    if c:
        elements.append(c)

    if d:
        elements.append(d)

    return "-".join(elements)
