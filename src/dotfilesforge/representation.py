import textwrap

from typing_extensions import cast

PAD = "  "  # 2 spaces, used everywhere


def format_value(value: object) -> str:
    if isinstance(value, dict):
        return format_dict(cast(dict[str, object], value))
    elif hasattr(value, "__dict__") and not isinstance(value, type):
        return build_repr(value)
    return repr(value)


def format_dict(d: dict[str, object]) -> str:
    inner = textwrap.indent(
        ",\n".join(f"{key!r}: {format_value(value)}" for key, value in d.items()),
        PAD,
    )
    return "{\n" + inner + "\n}"


def build_repr(obj: object) -> str:
    variables = cast(dict[str, object], obj.__dict__)
    fields = [f"{name} = {format_value(value)}" for name, value in variables.items()]
    inner = textwrap.indent(",\n".join(fields), PAD)
    return f"{obj.__class__.__name__}(\n{inner}\n)"
