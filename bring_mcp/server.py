"""Bring! shopping list MCP server."""

import os
import time
import httpx
from fastmcp import FastMCP

BASE_URL = "https://api.getbring.com/rest"

# Fixed public API key used by all Bring! clients
_CLIENT_HEADERS = {
    "X-BRING-API-KEY": "cof4Nc6D8saplXjE3h3HXqHH8m7VU2i1Gs0g85Sp",
    "X-BRING-CLIENT": "android",
    "X-BRING-APPLICATION": "bring",
    "X-BRING-COUNTRY": "US",
}

mcp = FastMCP("bring")

# Session state (populated on first use via lazy auth)
_session: dict = {}


def _auth_headers() -> dict:
    """Return headers for authenticated requests, refreshing token if expired."""
    if not _session:
        _authenticate()
    elif _session.get("expires_at", 0) < time.time() + 60:
        _refresh_token()
    return {
        **_CLIENT_HEADERS,
        "Authorization": f"Bearer {_session['access_token']}",
        "X-BRING-USER-UUID": _session["uuid"],
        "X-BRING-PUBLIC-USER-UUID": _session["publicUuid"],
    }


def _authenticate() -> None:
    """Authenticate with Bring! using BRING_EMAIL and BRING_PASSWORD env vars."""
    email = os.environ.get("BRING_EMAIL")
    password = os.environ.get("BRING_PASSWORD")
    if not email or not password:
        raise RuntimeError("BRING_EMAIL and BRING_PASSWORD environment variables are required")

    resp = httpx.post(
        f"{BASE_URL}/v2/bringauth",
        data={"email": email, "password": password},
        headers=_CLIENT_HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    _session.clear()
    _session.update({
        "uuid": data["uuid"],
        "publicUuid": data.get("publicUuid", data["uuid"]),
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", ""),
        "expires_at": time.time() + data.get("expires_in", 3600),
    })


def _refresh_token() -> None:
    """Refresh the bearer token using the stored refresh token."""
    resp = httpx.post(
        f"{BASE_URL}/v2/bringauth/token",
        data={"grant_type": "refresh_token", "refresh_token": _session["refresh_token"]},
        headers=_CLIENT_HEADERS,
        timeout=15,
    )
    if resp.status_code != 200:
        # Fall back to full re-auth if refresh fails
        _authenticate()
        return
    data = resp.json()
    _session["access_token"] = data["access_token"]
    _session["expires_at"] = time.time() + data.get("expires_in", 3600)
    if "refresh_token" in data:
        _session["refresh_token"] = data["refresh_token"]


@mcp.tool
def get_lists() -> dict:
    """Retrieve all Bring! shopping lists for the authenticated user.

    Returns a dict with a 'lists' key containing objects with 'listUuid',
    'name', and 'theme' fields.
    """
    headers = _auth_headers()
    resp = httpx.get(
        f"{BASE_URL}/bringusers/{_session['uuid']}/lists",
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def get_list_items(list_uuid: str) -> dict:
    """Get the items in a specific Bring! shopping list.

    Args:
        list_uuid: The UUID of the shopping list (from get_lists).

    Returns a dict with an 'items' key containing 'purchase' and 'recently'
    arrays. Each item has 'itemId' and 'specification' fields.
    """
    resp = httpx.get(
        f"{BASE_URL}/v2/bringlists/{list_uuid}",
        headers=_auth_headers(),
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


@mcp.tool
def add_item(list_uuid: str, item_id: str, specification: str = "") -> dict:
    """Add an item to a Bring! shopping list.

    Args:
        list_uuid: The UUID of the target shopping list.
        item_id: The item name / catalog ID (e.g. "Milk", "Bananas").
        specification: Optional detail appended to the item (e.g. "2 liters", "organic").

    Returns the raw API response confirming the change.
    """
    resp = httpx.put(
        f"{BASE_URL}/v2/bringlists/{list_uuid}/items",
        json={
            "changes": [{
                "itemId": item_id,
                "spec": specification,
                "operation": "TO_PURCHASE",
                "accuracy": "0.0",
                "altitude": "0.0",
                "latitude": "0.0",
                "longitude": "0.0",
            }],
            "sender": "",
        },
        headers=_auth_headers(),
        timeout=15,
    )
    resp.raise_for_status()
    return {"status": "added", "itemId": item_id, "specification": specification}


@mcp.tool
def remove_item(list_uuid: str, item_id: str) -> dict:
    """Permanently remove an item from a Bring! shopping list.

    Args:
        list_uuid: The UUID of the shopping list.
        item_id: The item name / ID to remove (must match exactly as stored).

    Returns a confirmation dict.
    """
    resp = httpx.put(
        f"{BASE_URL}/v2/bringlists/{list_uuid}/items",
        json={
            "changes": [{
                "itemId": item_id,
                "spec": "",
                "operation": "REMOVE",
                "accuracy": "0.0",
                "altitude": "0.0",
                "latitude": "0.0",
                "longitude": "0.0",
            }],
            "sender": "",
        },
        headers=_auth_headers(),
        timeout=15,
    )
    resp.raise_for_status()
    return {"status": "removed", "itemId": item_id}


@mcp.tool
def move_item_to_recently_used(list_uuid: str, item_id: str, specification: str = "") -> dict:
    """Move an item from the active purchase list to the recently-used section.

    This is equivalent to checking off an item in the Bring! app — it stays
    visible in 'recently used' so it can be quickly re-added later.

    Args:
        list_uuid: The UUID of the shopping list.
        item_id: The item name / ID to move.
        specification: The item's current specification (preserves it in history).

    Returns a confirmation dict.
    """
    resp = httpx.put(
        f"{BASE_URL}/v2/bringlists/{list_uuid}/items",
        json={
            "changes": [{
                "itemId": item_id,
                "spec": specification,
                "operation": "TO_RECENTLY",
                "accuracy": "0.0",
                "altitude": "0.0",
                "latitude": "0.0",
                "longitude": "0.0",
            }],
            "sender": "",
        },
        headers=_auth_headers(),
        timeout=15,
    )
    resp.raise_for_status()
    return {"status": "moved_to_recently_used", "itemId": item_id}


@mcp.tool
def get_catalog_items(query: str, locale: str = "en-US") -> dict:
    """Search the Bring! catalog for item name suggestions.

    Fetches the full locale catalog from Bring! and returns items whose
    names contain the query string (case-insensitive). Use this to find
    the canonical item ID before calling add_item.

    Args:
        query: Search term to filter catalog items (e.g. "milk", "bread").
        locale: BCP-47 locale for the catalog (default "en-US").
                Common values: "de-DE", "en-US", "fr-FR", "es-ES".

    Returns a dict with a 'results' list of matching {'itemId', 'name'} objects
    and a 'total_in_catalog' count.
    """
    resp = httpx.get(
        f"{BASE_URL}/bringcatalog/{locale}",
        headers=_auth_headers(),
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()

    # Catalog shape: {"catalog": {"items": [{"itemId": str, "name": str}, ...]}}
    all_items: list[dict] = (
        data.get("catalog", data).get("items", [])
        if isinstance(data.get("catalog"), dict)
        else data.get("items", [])
    )

    query_lower = query.lower()
    matches = [
        {"itemId": item.get("itemId", item.get("name", "")), "name": item.get("name", "")}
        for item in all_items
        if query_lower in item.get("name", "").lower()
    ]
    return {"results": matches, "total_in_catalog": len(all_items)}


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
