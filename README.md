# ramp-mcp: A Ramp MCP server

## Overview

A Model Context Protocol server for retrieving and analyzing data or running tasks for [Ramp](https://ramp.com) using [Developer API](https://docs.ramp.com/developer-api/v1/overview/introduction). In order to get around token and input size limitations, this server implements a simple ETL pipeline + ephemeral sqlite database in memory for analysis by an LLM. All requests are made to demo by default, but can be changed by setting `RAMP_ENV=prd`. Large datasets may not be processable due to API and/or your MCP client limitations.

### Tools

#### Database tools

Tools that can be used to setup, process, query, and delete an ephemeral database in memory.

1. `process_data`
2. `execute_query`
3. `clear_table`

#### Fetch tools

Tools that can be used to fetch data directly

1. `get_ramp_categories`
2. `get_currencies`

#### Load tools

Loads data to server which the client can fetch. Based on the tools you wish to use, ensure to enable those scopes on your
Ramp client and include the scopes when starting the server as a CLI argument.

| Tool                      | Scope               |
| ------------------------- | ------------------- |
| load_transactions         | transactions:read   |
| load_reimbursements       | reimbursements:read |
| load_bills                | bills:read          |
| load_locations            | locations:read      |
| load_departments          | departments:read    |
| load_bank_accounts        | bank_accounts:read  |
| load_vendors              | vendors:read        |
| load_vendor_bank_accounts | vendors:read        |
| load_entities             | entities:read       |
| load_spend_limits         | limits:read         |
| load_spend_programs       | spend_programs:read |
| load_users                | users:read          |

For large datasets, it is recommended to explicitly prompt Claude not to use REPL and to keep responses concise to avoid timeout or excessive token usage.

## Setup

### Ramp Setup

The MCP server supports two authentication methods:

#### Option 1: Client Credentials Flow (Shared Application Access)
1. Create a new client from the Ramp developer page (Profile on top right > Developer > Create app)
2. Grant the scopes you wish (based on tools) to the client and enable client credentials (Click on App > Grant Types / Scopes)
3. Include the client ID and secret in the config file as well as the scopes you wish to use

#### Option 2: OAuth2 Access Token (Individual Employee Access)
1. Create a new client from the Ramp developer page and enable OAuth2 authorization code flow
2. Implement OAuth2 flow in your application to obtain an access token for each employee
3. Use the access token directly with the MCP server for employee-specific access

**Note**: OAuth2 access tokens provide employee-scoped access, meaning each employee can only access data they have permissions for in Ramp. This is ideal for individual employee usage scenarios.

### Local Setup

1. Clone this Github repo via `git clone git@github.com:ramp/ramp-mcp.git` or equivalent
2. Install [`uv`](https://docs.astral.sh/uv/)

## Usage

### Using Client Credentials Flow

Run the MCP server from your CLI with:

```bash
RAMP_CLIENT_ID=... RAMP_CLIENT_SECRET=... RAMP_ENV=<demo|prd> uv run ramp-mcp -s <COMMA-SEPARATED-SCOPES>
```

### Using OAuth2 Access Token

Run the MCP server from your CLI with:

```bash
RAMP_ACCESS_TOKEN=... RAMP_ENV=<demo|prd> uv run ramp-mcp -s <COMMA-SEPARATED-SCOPES>
```

**Important**: When using OAuth2 access tokens, ensure the token has the required scopes for the tools you want to use. The scopes parameter is still required for tool registration, but the actual API access is limited by the token's granted scopes.

## Configuration

### Usage with Claude Desktop

#### Using Client Credentials Flow

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ramp-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/<ABSOLUTE-PATH-TO>/ramp-mcp", // make sure to update this path
        "run",
        "ramp-mcp",
        "-s",
        "transactions:read,reimbursements:read"
      ],
      "env": {
        "RAMP_CLIENT_ID": "<CLIENT_ID>",
        "RAMP_CLIENT_SECRET": "<CLIENT_SECRET>",
        "RAMP_ENV": "<demo|qa|prd>"
      }
    }
  }
}
```

#### Using OAuth2 Access Token

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ramp-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/<ABSOLUTE-PATH-TO>/ramp-mcp", // make sure to update this path
        "run",
        "ramp-mcp",
        "-s",
        "transactions:read,reimbursements:read"
      ],
      "env": {
        "RAMP_ACCESS_TOKEN": "<ACCESS_TOKEN>",
        "RAMP_ENV": "<demo|qa|prd>"
      }
    }
  }
}
```

If this file doesn't exist yet, create one in `/<ABSOLUTE-PATH-TO>/Library/Application Support/Claude/`

## License

Copyright (c) 2025, Ramp Business Corporation
All rights reserved.
This source code is licensed under the MIT License found in the LICENSE file in the root directory of this source tree.
