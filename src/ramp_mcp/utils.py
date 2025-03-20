import datetime
from typing import Any


def str_date_to_datetime(date_str: str, add_one_day: bool = False) -> datetime.datetime:
    date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    if add_one_day:
        # easier than explaining exclusive end date
        date += datetime.timedelta(days=1)
    return date.astimezone(datetime.timezone.utc)


def get_nested_keys(data: dict[str, Any]) -> list[str]:
    """
    Get all keys including nested keys as a dot-separated string
    e.g. {"a": {"b": "c"}, "d": "e"} -> ["a__b", "d"]
    """
    stack = [(key, value, key) for key, value in data.items()]
    keys = []

    while stack:
        _, value, path = stack.pop()

        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if path == sub_key:
                    # hack for tie breakers
                    new_path = f"{path}__{sub_key}_1"
                else:
                    new_path = f"{path}__{sub_key}"
                stack.append((sub_key, sub_value, new_path))
        else:
            keys.append(path)

    return keys
