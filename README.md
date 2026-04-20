# mcp-bring-server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

MCP server that connects Claude to the [Bring!](https://getbring.com) shopping list app.

## Tools

| Tool | Description |
|------|-------------|
| `get_lists` | Retrieve all your shopping lists |
| `get_list_items` | Get items in a list (purchase + recently used) |
| `add_item` | Add an item with optional specification |
| `remove_item` | Permanently remove an item |
| `move_item_to_recently_used` | Check off an item (moves it to recently used) |
| `get_catalog_items` | Search the Bring! catalog for item suggestions |

## Setup

### Prerequisites

- [uv](https://docs.astral.sh/uv/) installed
- A Bring! account

### Environment variables

```bash
export BRING_EMAIL="you@example.com"
export BRING_PASSWORD="your-password"
```

### Install as a Cowork plugin

```bash
claude plugin install /path/to/mcp-bring-server
```

Then set the required env vars in your shell profile or via `claude plugin env set bring BRING_EMAIL=... BRING_PASSWORD=...`.

### Manual Claude Code setup

Add to your `~/.claude/settings.json` under `mcpServers`:

```json
{
  "mcpServers": {
    "bring": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/mcp-bring-server", "bring-mcp"],
      "env": {
        "BRING_EMAIL": "you@example.com",
        "BRING_PASSWORD": "your-password"
      }
    }
  }
}
```

## Notes

- Authentication is lazy: the server authenticates on the first tool call and auto-refreshes the bearer token before expiry.
- The Bring! API is community-documented and unofficial; endpoint behavior may change.
- `get_catalog_items` fetches the full locale catalog and filters client-side. Pass `locale` (e.g. `"de-DE"`) matching your Bring! account's language for best results.

## Disclaimer

This project is not affiliated with or endorsed by Bring! Labs AG. It uses the community-documented Bring! REST API and is provided as-is for personal use.

## License

[MIT](LICENSE) © Jose Leos
