import json
import sqlite3
from pydantic import BaseModel
from typing import Any, Type, Union, get_origin, get_args

type_mapping = {
    "str": "TEXT",
    "int": "INTEGER",
    "float": "REAL",
    "bool": "INTEGER",
    "bytes": "BLOB",
    "datetime": "TEXT",
    "date": "TEXT",
    "time": "TEXT",
    "dict": "JSON",
    "list": "JSON",
}


def get_inner_type(field_type: Any) -> Any:
    """
    Get the inner type of a Union or Optional (otherwise return the type itself).
    """
    if get_origin(field_type) is Union:
        args = get_args(field_type)
        # Filter out NoneType to get the actual type
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1:
            return non_none_args[0]

    return field_type


def type_str(field_type: Any) -> str:
    """
    Convert a python type to a string representation so it can be mapped to a SQL type.
    """
    actual_type = get_inner_type(field_type)

    origin = get_origin(actual_type)
    if origin is list:
        return "list"
    elif origin is dict:
        return "dict"
    else:
        return str(actual_type).split("'")[1].split(".")[-1]


def not_null_constraint(
    model: Type[BaseModel], field_name: str, field_type: Any
) -> str:
    """
    Generate a NOT NULL constraint for a field if it is required.
    """
    field_info = model.model_fields[field_name]
    return (
        " NOT NULL"
        if field_info.is_required and type(None) not in get_args(field_type)
        else ""
    )


def create_table(model: Type[BaseModel], table_name: str) -> str:
    """
    Generate a SQLite CREATE TABLE statement from a Pydantic model.

    :param model: Pydantic model class
    :param table_name: Name of the table to create
    :return: SQLite CREATE TABLE statement as a string
    """
    fields = model.__annotations__
    columns = []

    for field_name, field_type in fields.items():
        field_type_str = type_str(field_type)
        sqlite_type = type_mapping.get(
            field_type_str, "TEXT"
        )  # Default to TEXT if type not found

        not_null = not_null_constraint(model, field_name, field_type)
        columns.append(f"{field_name} {sqlite_type}{not_null}")

    columns_str = ", ".join(columns)
    create_table_statement = (
        "CREATE TABLE IF NOT EXISTS " + f"{table_name}({columns_str});"
    )

    return create_table_statement


def serialize_model(model: BaseModel) -> dict[str, Any]:
    serialized_dict: dict[str, int | float | str | bool | None] = {}

    for key, value in model.model_dump().items():
        if isinstance(value, (int, float, str, bool)):
            serialized_dict[key] = value
        elif isinstance(value, (list, dict)):
            serialized_dict[key] = json.dumps(value)
        elif value is None:
            serialized_dict[key] = None
        else:
            raise ValueError(f"Unsupported type for key '{
                             key}': {type(value)}")

    return serialized_dict


def create_insert_statement(model: BaseModel, table_name: str) -> str:
    fields = model.model_fields.keys()
    placeholders = ", ".join([f":{field}" for field in fields])
    field_names = ", ".join(fields)
    return f"INSERT INTO {table_name} ({field_names}) VALUES ({placeholders})"


def insert(conn: sqlite3.Cursor, model: BaseModel, table_name: str) -> None:
    sql = create_insert_statement(model, table_name)
    conn.execute(sql, serialize_model(model))
