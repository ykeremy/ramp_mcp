import click
from mcp.server.fastmcp import FastMCP

from ramp_mcp.tools import (
    clear_table,
    execute_query,
    get_currencies,
    get_ramp_categories,
    load_bank_accounts,
    load_bills,
    load_departments,
    load_entities,
    load_locations,
    load_receipts,
    load_reimbursements,
    load_spend_export,
    load_spend_limits,
    load_spend_programs,
    load_transactions,
    load_users,
    load_vendor_bank_accounts,
    load_vendors,
    process_data,
    ramp_client,
)

server = FastMCP(
    "ramp-mcp",
    instructions="""
    Ramp is a platform for corporate cards, bill payments, accounting,
    and a whole lot more. Data is made available via the developer API.
    - For performance, always try to load all of the data needed
    prior to setting up tables or running queries. Use as many window functions
    as possible.
    - Ensure that all calculations are accurate.
    """,
    dependencies=["httpx", "iso4217", "flatten_json"],
)

scope_to_tools_mapping = {
    # load tools
    "transactions:read": [load_transactions],
    "receipts:read": [load_receipts],
    "reimbursements:read": [load_reimbursements],
    "bills:read": [load_bills],
    "locations:read": [load_locations],
    "departments:read": [load_departments],
    "bank_accounts:read": [load_bank_accounts],
    "vendors:read": [load_vendors, load_vendor_bank_accounts],
    "entities:read": [load_entities],
    "limits:read": [load_spend_limits],
    "spend_programs:read": [load_spend_programs],
    "users:read": [load_users],
}


@click.command()
@click.option(
    "--scopes",
    "-s",
    type=click.STRING,
    default="transactions:read,reimbursements:read,bills:read",
    help=f"""
    Comma seperated list of scopes to use. Do not include spaces.
    Available scopes: {", ".join(scope_to_tools_mapping.keys())}
    """,
)
def main(scopes: str):
    # register load tools based on scopes
    scopes = scopes.split(",")
    for scope in scopes:
        if scope not in scope_to_tools_mapping:
            continue
        for tool in scope_to_tools_mapping[scope]:
            server.add_tool(tool)

    # special tool that requires all three scopes
    if all(
        scope in scopes
        for scope in ["transactions:read", "reimbursements:read", "bills:read"]
    ):
        server.add_tool(load_spend_export)

    # always register fetch tools
    server.add_tool(get_ramp_categories)
    server.add_tool(get_currencies)
    server.add_tool(clear_table)
    server.add_tool(process_data)
    server.add_tool(execute_query)

    ramp_client.connect(scopes)

    server.run(transport="stdio")


if __name__ == "__main__":
    main()


__all__ = ["main", "server"]
