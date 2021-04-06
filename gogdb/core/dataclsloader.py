import dataclasses
import typing
import datetime


def get_origin(t):
    """Typing function defined here for compatibility with Python 3.7"""
    return getattr(t, "__origin__", None)

def get_args(t):
    """Typing function defined here for compatibility with Python 3.7"""
    return getattr(t, "__args__", None)

annotations_cache = {}
def class_from_json(cls, data):
    if data is None:
        return None
    if dataclasses.is_dataclass(cls):
        if cls in annotations_cache:
            annotations = annotations_cache.get(cls)
        else:
            annotations = typing.get_type_hints(cls)
            annotations_cache[cls] = annotations
        inst = cls()
        for field_name, field_value in data.items():
            try:
                field_type = annotations[field_name]
            except KeyError:
                raise KeyError("Invalid field {!r} in json. Valid fields for type {}: {!r}".format(
                    field_name, cls, list(annotations.keys())))
            try:
                field_inst = class_from_json(field_type, field_value)
            except TypeError:
                raise TypeError(f"Failed to parse field {field_name}")
            setattr(inst, field_name, field_inst)
        return inst
    elif get_origin(cls) is list:
        list_element_type = typing.get_args(cls)[0]
        return [
            class_from_json(list_element_type, list_element) for
            list_element in data]
    elif cls is datetime.datetime:
        return datetime.datetime.fromisoformat(data)
    else:
        if cls is not typing.Any:
            if not (type(data) is cls or data is None):
                raise TypeError(f"{repr(data)} is of type {type(data)}, {cls} required")
        return data

