from functools import wraps
from typing import Any, Literal

from iso4217 import Currency

from .client import RampAsyncClient
from .constants import (
    AMOUNT_DESCRIPTION,
    SK_CATEGORIES,
)
from .memory_db import MemoryDatabase
from .types import Role
from .utils import get_nested_keys, str_date_to_datetime

ramp_client = RampAsyncClient()
memory_db = MemoryDatabase()


def handle_response(func):
    """
    Wrap every tool with this to handle errors
    """

    @wraps(func)
    async def wrapper(*args, **kwargs) -> str | list[dict[str, Any]]:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            return (
                f"Ran into an error: {e}\n"
                "Communicate this to the user and consider retrying "
                "if the error seems transient.\n"
            )

    return wrapper


def handle_load_response(func):
    """
    Wrap every load tool with this
    """

    @wraps(func)
    @handle_response
    async def wrapper(*args, **kwargs) -> str:
        data = await func(*args, **kwargs)
        if not data:
            return "No data found\n"
        # hack to help us get past claude's context window and input size limitations
        name = memory_db.store_data(func.__name__, data)
        return (
            f"Stored data in memory database with table name: {name}.\n "
            f"Call `process_data` tool with table name and desired columns to setup a SQL table.\n "
            f"Call `execute_query` tool with query to get results as a JSON.\n "
            f"Available columns are: {', '.join(get_nested_keys(data[0]))}\n"
            f"Call `clear_table` tool with table name to delete the table from the memory database.\n"
        )

    return wrapper


# ================================================
# Database tools
# ================================================
@handle_response
async def clear_table(table_name: str) -> str:
    """
    Clear a table
    """
    memory_db.clear_table(table_name)
    return f"Table {table_name} cleared"


@handle_response
async def process_data(table_name: str, cols: list[str]) -> str:
    """
    Process data into a table
    """
    if memory_db.data_is_processed(table_name):
        return f"Table {table_name} already processed"
    memory_db.create_table_with_cols(table_name, cols)
    memory_db.load_data(table_name)
    memory_db.commit(table_name)
    return f"Table {table_name} created"


@handle_response
async def execute_query(table_name: str, query: str) -> list[dict[str, Any]] | str:
    f"""
    Execute a SQL query on a table and return results as a list of objects
    Use sqlite syntax and use window functions whenever possible.
    {AMOUNT_DESCRIPTION}
    """
    if not memory_db.exists(table_name):
        return f"Error: table {table_name} does not exist"
    return memory_db.execute_query(query)


# ================================================
# Fetch tools
# ================================================
@handle_response
async def get_ramp_categories() -> list[dict[str, Any]]:
    """
    Get Ramp transaction categories
    """
    return [{"id": k, "name": v} for k, v in SK_CATEGORIES.items()]


@handle_response
async def get_currencies() -> list[dict[str, Any]]:
    """
    Get currencies
    """
    return [
        {"currency_code": val.code, "currency_name": val.currency_name}
        for val in Currency
    ]


# ================================================
# Load tools
# ================================================
@handle_load_response
async def load_transactions(
    from_date: str,
    to_date: str,
    user_id: str | None = None,
    card_id: str | None = None,
    ramp_category_ids: list[str] = [],
    accounting_sync_ready: bool | None = None,
) -> list[dict[str, Any]]:
    f"""
    Transactions are sorted by amount in descending order and only represent card transactions.
    {AMOUNT_DESCRIPTION}
    """
    params = {
        "from_date": str_date_to_datetime(from_date),
        "to_date": str_date_to_datetime(to_date, add_one_day=True),
        "order_by_amount_desc": True,
    }
    if user_id:
        params["user_id"] = user_id
    if ramp_category_ids:
        params["sk_category_ids"] = ramp_category_ids
    if card_id:
        params["card_id"] = card_id
    if accounting_sync_ready is not None:
        params["sync_ready"] = accounting_sync_ready

    return await ramp_client.paginate_list_endpoint(
        "/transactions",
        params,
    )


@handle_load_response
async def load_spend_export(
    from_date: str,
    to_date: str,
) -> list[dict[str, Any]]:
    """
    Spend export is a list of all spend events (transactions, reimbursements, bills etc.) for a user.
    Always use this over load_transactions, load_reimbursements, load_bills, etc. when possible
    """
    params = {
        "from_date": str_date_to_datetime(from_date),
        "to_date": str_date_to_datetime(to_date, add_one_day=True),
    }
    if from_date:
        params["from_date"] = str_date_to_datetime(from_date)
    if to_date:
        params["to_date"] = str_date_to_datetime(to_date, add_one_day=True)

    return await ramp_client.paginate_list_endpoint(
        "/spend-export",
        params,
    )


@handle_load_response
async def load_receipts(
    from_date: str,
    to_date: str,
    transaction_id: str | None = None,
    created_before: str | None = None,
    created_after: str | None = None,
) -> list[dict[str, Any]]:
    f"""
    Get receipts
    {AMOUNT_DESCRIPTION}
    """
    params = {
        "from_date": str_date_to_datetime(from_date),
        "to_date": str_date_to_datetime(to_date, add_one_day=True),
        "order_by_amount_desc": True,
    }
    if transaction_id:
        params["transaction_id"] = transaction_id
    if created_before:
        params["created_before"] = str_date_to_datetime(created_before)
    if created_after:
        params["created_after"] = str_date_to_datetime(created_after, add_one_day=True)

    return await ramp_client.paginate_list_endpoint(
        "/receipts",
        params,
    )


@handle_load_response
async def load_reimbursements(
    from_date: str,
    to_date: str,
    sync_ready: bool | None = None,
    direction: Literal["BUSINESS_TO_USER", "USER_TO_BUSINESS", ""] = "",
    user_id: str | None = None,
) -> list[dict[str, Any]]:
    f"""
    Get reimbursements for user
    {AMOUNT_DESCRIPTION}
    """
    params = {
        "from_date": str_date_to_datetime(from_date),
        "to_date": str_date_to_datetime(to_date, add_one_day=True),
    }
    if sync_ready is not None:
        params["sync_ready"] = sync_ready
    if direction:
        params["direction"] = direction
    if user_id:
        params["user_id"] = user_id

    return await ramp_client.paginate_list_endpoint(
        "/reimbursements",
        params,
    )


@handle_load_response
async def load_bills(
    from_date: str,
    to_date: str,
    payment_status: Literal["OPEN", "PAID", ""] = "",
    user_id: str | None = None,
    acccounting_sync_ready: bool | None = None,
) -> list[dict[str, Any]]:
    f"""
    Get bills for user
    {AMOUNT_DESCRIPTION}
    """
    params = {
        "from_created_at": str_date_to_datetime(from_date),
        "to_created_at": str_date_to_datetime(to_date, add_one_day=True),
    }
    if user_id:
        params["user_id"] = user_id
    if acccounting_sync_ready is not None:
        params["sync_ready"] = acccounting_sync_ready
    if payment_status:
        params["payment_status"] = payment_status

    return await ramp_client.paginate_list_endpoint(
        "/bills",
        params,
    )


@handle_load_response
async def load_locations(
    entity_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Get locations for entity
    """
    params = {}
    if entity_id:
        params["entity_id"] = entity_id

    return await ramp_client.paginate_list_endpoint(
        "/locations",
        params,
    )


@handle_load_response
async def load_departments() -> list[dict[str, Any]]:
    """
    Get departments
    """
    return await ramp_client.paginate_list_endpoint(
        "/departments",
        {},
    )


@handle_load_response
async def load_bank_accounts(
    bank_account_id: str,
) -> list[dict[str, Any]]:
    """
    Get bank accounts for own business/entities.
    """
    params = {}
    if bank_account_id:
        params["bank_account_id"] = bank_account_id

    return await ramp_client.paginate_list_endpoint(
        "/bank_accounts",
        params,
    )


@handle_load_response
async def load_vendors(
    ramp_category_ids: list[str] = [],
    is_active: bool | None = True,
    name: str | None = None,
    from_created_at: str | None = None,
    to_created_at: str | None = None,
) -> list[dict[str, Any]]:
    """
    Get vendors for user

    Usually search for only active vendors.
    """
    params = {}
    if ramp_category_ids:
        params["sk_category_ids"] = ramp_category_ids
    if is_active is not None:
        params["is_active"] = is_active
    if name:
        params["name"] = name
    if from_created_at:
        params["from_created_at"] = str_date_to_datetime(from_created_at)
    if to_created_at:
        params["to_created_at"] = str_date_to_datetime(to_created_at, add_one_day=True)

    return await ramp_client.paginate_list_endpoint(
        "/vendors",
        params,
    )


@handle_load_response
async def load_vendor_bank_accounts(
    vendor_id: str,
) -> list[dict[str, Any]]:
    """
    Get bank accounts for vendors
    """
    params = {}

    return await ramp_client.paginate_list_endpoint(
        f"/vendors/{vendor_id}/accounts",
        params,
    )


@handle_load_response
async def load_entities(
    entity_name: str | None = None,
) -> list[dict[str, Any]]:
    """
    Get entities for user
    """
    params = {}
    if entity_name:
        params["entity_name"] = entity_name

    return await ramp_client.paginate_list_endpoint(
        "/entities",
        params,
    )


@handle_load_response
async def load_spend_limits(
    user_id: str | None = None,
) -> list[dict[str, Any]]:
    """
    Get limits for user
    """
    params = {}
    if user_id:
        params["user_id"] = user_id

    return await ramp_client.paginate_list_endpoint(
        "/limits",
        params,
    )


@handle_load_response
async def load_spend_programs() -> list[dict[str, Any]]:
    """
    Get spend programs
    """
    return await ramp_client.paginate_list_endpoint(
        "/spend-programs",
        {},
    )


@handle_load_response
async def load_users(
    email: str | None = None,
    role: Role = "",
) -> list[dict[str, Any]]:
    """
    Get users from Ramp
    """
    params = {}
    if email:
        params["email"] = email
    if role:
        params["role"] = role

    return await ramp_client.paginate_list_endpoint(
        "/users",
        params,
    )
