#!/usr/bin/env python3
"""
Hudu REST API client — urllib.request based, no external dependencies.
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional


class HuduClient:
    def __init__(self, auth):
        self._auth = auth
        self._base = auth.base_api_url

    @staticmethod
    def _unwrap(data):
        """Unwrap single-resource responses: {"article": {...}} → {...}"""
        if isinstance(data, dict) and len(data) == 1:
            val = next(iter(data.values()))
            if isinstance(val, (dict, list)):
                return val
        return data

    def _request(self, method: str, path: str, params: Optional[dict] = None, body: Optional[dict] = None) -> Any:
        url = f"{self._base}{path}"
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            if clean:
                url = f"{url}?{urllib.parse.urlencode(clean)}"

        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, headers=self._auth.auth_headers(), method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw.strip() else None
        except urllib.error.HTTPError as e:
            body_text = e.read().decode(errors="replace")
            try:
                err = json.loads(body_text)
                msg = err.get("error") or err.get("message") or body_text
            except Exception:
                msg = body_text
            sys.exit(f"HTTP {e.code} {method} {path}: {msg}")
        except urllib.error.URLError as e:
            sys.exit(f"Request failed ({method} {path}): {e.reason}")

    def _paginate(self, path: str, params: Optional[dict] = None, page_size: int = 25) -> list:
        params = dict(params or {})
        params["page_size"] = page_size
        results = []
        page = 1
        while True:
            params["page"] = page
            data = self._request("GET", path, params=params)
            if isinstance(data, list):
                chunk = data
            elif isinstance(data, dict):
                chunk = next((v for v in data.values() if isinstance(v, list)), [])
            else:
                break
            results.extend(chunk)
            if len(chunk) < page_size:
                break
            page += 1
        return results

    # -------------------------------------------------------------------------
    # API Info
    # -------------------------------------------------------------------------

    def get_api_info(self):
        return self._request("GET", "/api_info")

    # -------------------------------------------------------------------------
    # Companies
    # -------------------------------------------------------------------------

    def list_companies(self, name=None, search=None, page_size=25):
        params = {"name": name, "search": search}
        return self._paginate("/companies", params, page_size)

    def get_company(self, company_id: int):
        return self._unwrap(self._request("GET", f"/companies/{company_id}"))

    def create_company(self, name: str, **kwargs):
        body = {"company": {"name": name, **kwargs}}
        return self._unwrap(self._request("POST", "/companies", body=body))

    def update_company(self, company_id: int, **kwargs):
        body = {"company": kwargs}
        return self._unwrap(self._request("PUT", f"/companies/{company_id}", body=body))

    def delete_company(self, company_id: int):
        return self._request("DELETE", f"/companies/{company_id}")

    def archive_company(self, company_id: int):
        return self._unwrap(self._request("PUT", f"/companies/{company_id}/archive"))

    def unarchive_company(self, company_id: int):
        return self._unwrap(self._request("PUT", f"/companies/{company_id}/unarchive"))

    # -------------------------------------------------------------------------
    # Articles (Knowledge Base)
    # -------------------------------------------------------------------------

    def list_articles(self, company_id=None, name=None, search=None, draft=None, page_size=25):
        params = {"company_id": company_id, "name": name, "search": search, "draft": draft}
        return self._paginate("/articles", params, page_size)

    def get_article(self, article_id: int):
        return self._unwrap(self._request("GET", f"/articles/{article_id}"))

    def create_article(self, name: str, content: str, company_id: int = None, **kwargs):
        body = {"article": {"name": name, "content": content, **kwargs}}
        if company_id:
            body["article"]["company_id"] = company_id
        return self._unwrap(self._request("POST", "/articles", body=body))

    def update_article(self, article_id: int, **kwargs):
        body = {"article": kwargs}
        return self._unwrap(self._request("PUT", f"/articles/{article_id}", body=body))

    def delete_article(self, article_id: int):
        return self._request("DELETE", f"/articles/{article_id}")

    def archive_article(self, article_id: int):
        return self._unwrap(self._request("PUT", f"/articles/{article_id}/archive"))

    # -------------------------------------------------------------------------
    # Assets
    # -------------------------------------------------------------------------

    def list_assets(self, company_id=None, asset_layout_id=None, name=None, search=None,
                    archived=None, page_size=25):
        params = {
            "company_id": company_id,
            "asset_layout_id": asset_layout_id,
            "name": name,
            "search": search,
            "archived": archived,
        }
        return self._paginate("/assets", params, page_size)

    def get_asset(self, asset_id: int, company_id: int = None):
        if company_id:
            return self._unwrap(self._request("GET", f"/companies/{company_id}/assets/{asset_id}"))
        # No standalone /assets/{id} endpoint — filter by id
        data = self._request("GET", "/assets", params={"id": asset_id})
        results = self._unwrap(data) if isinstance(data, dict) else data
        if isinstance(results, list):
            return results[0] if results else None
        return results

    def create_asset(self, company_id: int, name: str, asset_layout_id: int, **kwargs):
        body = {"asset": {"name": name, "asset_layout_id": asset_layout_id, **kwargs}}
        return self._unwrap(self._request("POST", f"/companies/{company_id}/assets", body=body))

    def _asset_company_id(self, asset_id: int) -> int:
        asset = self.get_asset(asset_id)
        if not asset or not asset.get("company_id"):
            import sys; sys.exit(f"Could not resolve company_id for asset {asset_id}")
        return asset["company_id"]

    def update_asset(self, asset_id: int, company_id: int = None, **kwargs):
        cid = company_id or self._asset_company_id(asset_id)
        body = {"asset": kwargs}
        return self._unwrap(self._request("PUT", f"/companies/{cid}/assets/{asset_id}", body=body))

    def delete_asset(self, asset_id: int, company_id: int = None):
        cid = company_id or self._asset_company_id(asset_id)
        return self._request("DELETE", f"/companies/{cid}/assets/{asset_id}")

    def archive_asset(self, asset_id: int, company_id: int = None):
        cid = company_id or self._asset_company_id(asset_id)
        return self._unwrap(self._request("PUT", f"/companies/{cid}/assets/{asset_id}/archive"))

    # -------------------------------------------------------------------------
    # Asset Layouts
    # -------------------------------------------------------------------------

    def list_asset_layouts(self, search=None, page_size=25):
        return self._paginate("/asset_layouts", {"search": search}, page_size)

    def get_asset_layout(self, layout_id: int):
        return self._unwrap(self._request("GET", f"/asset_layouts/{layout_id}"))

    def create_asset_layout(self, name: str, **kwargs):
        body = {"asset_layout": {"name": name, **kwargs}}
        return self._unwrap(self._request("POST", "/asset_layouts", body=body))

    def update_asset_layout(self, layout_id: int, **kwargs):
        body = {"asset_layout": kwargs}
        return self._unwrap(self._request("PUT", f"/asset_layouts/{layout_id}", body=body))

    # -------------------------------------------------------------------------
    # Asset Passwords
    # -------------------------------------------------------------------------

    def list_asset_passwords(self, company_id=None, name=None, search=None, page_size=25):
        params = {"company_id": company_id, "name": name, "search": search}
        return self._paginate("/asset_passwords", params, page_size)

    def get_asset_password(self, password_id: int):
        return self._unwrap(self._request("GET", f"/asset_passwords/{password_id}"))

    def create_asset_password(self, name: str, company_id: int, password: str = None, **kwargs):
        body = {"asset_password": {"name": name, "company_id": company_id, **kwargs}}
        if password:
            body["asset_password"]["password"] = password
        return self._unwrap(self._request("POST", "/asset_passwords", body=body))

    def update_asset_password(self, password_id: int, **kwargs):
        body = {"asset_password": kwargs}
        return self._unwrap(self._request("PUT", f"/asset_passwords/{password_id}", body=body))

    def delete_asset_password(self, password_id: int):
        return self._request("DELETE", f"/asset_passwords/{password_id}")

    # -------------------------------------------------------------------------
    # Procedures
    # -------------------------------------------------------------------------

    def list_procedures(self, company_id=None, name=None, search=None, page_size=25):
        params = {"company_id": company_id, "name": name, "search": search}
        return self._paginate("/procedures", params, page_size)

    def get_procedure(self, procedure_id: int):
        return self._unwrap(self._request("GET", f"/procedures/{procedure_id}"))

    def create_procedure(self, name: str, company_id: int = None, **kwargs):
        body = {"procedure": {"name": name, **kwargs}}
        if company_id:
            body["procedure"]["company_id"] = company_id
        return self._unwrap(self._request("POST", "/procedures", body=body))

    def update_procedure(self, procedure_id: int, **kwargs):
        body = {"procedure": kwargs}
        return self._unwrap(self._request("PUT", f"/procedures/{procedure_id}", body=body))

    def delete_procedure(self, procedure_id: int):
        return self._request("DELETE", f"/procedures/{procedure_id}")

    # -------------------------------------------------------------------------
    # Websites
    # -------------------------------------------------------------------------

    def list_websites(self, company_id=None, search=None, paused=None, page_size=25):
        params = {"company_id": company_id, "search": search, "paused": paused}
        return self._paginate("/websites", params, page_size)

    def get_website(self, website_id: int):
        return self._unwrap(self._request("GET", f"/websites/{website_id}"))

    def create_website(self, name: str, website_url: str, company_id: int = None, **kwargs):
        body = {"website": {"name": name, "website_url": website_url, **kwargs}}
        if company_id:
            body["website"]["company_id"] = company_id
        return self._unwrap(self._request("POST", "/websites", body=body))

    def update_website(self, website_id: int, **kwargs):
        body = {"website": kwargs}
        return self._unwrap(self._request("PUT", f"/websites/{website_id}", body=body))

    def delete_website(self, website_id: int):
        return self._request("DELETE", f"/websites/{website_id}")

    # -------------------------------------------------------------------------
    # Networks
    # -------------------------------------------------------------------------

    def list_networks(self, company_id=None, search=None, page_size=25):
        # Networks endpoint does not accept page_size — returns all results at once
        params = {k: v for k, v in {"company_id": company_id, "search": search}.items() if v is not None}
        data = self._request("GET", "/networks", params=params or None)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return next((v for v in data.values() if isinstance(v, list)), [])
        return []

    def get_network(self, network_id: int):
        return self._unwrap(self._request("GET", f"/networks/{network_id}"))

    # -------------------------------------------------------------------------
    # Users
    # -------------------------------------------------------------------------

    def list_users(self, search=None, page_size=25):
        return self._paginate("/users", {"search": search}, page_size)

    def get_user(self, user_id: int):
        return self._unwrap(self._request("GET", f"/users/{user_id}"))

    # -------------------------------------------------------------------------
    # Folders
    # -------------------------------------------------------------------------

    def list_folders(self, company_id=None, search=None, page_size=25):
        params = {"company_id": company_id, "search": search}
        return self._paginate("/folders", params, page_size)

    def get_folder(self, folder_id: int):
        return self._unwrap(self._request("GET", f"/folders/{folder_id}"))

    # -------------------------------------------------------------------------
    # Activity Logs
    # -------------------------------------------------------------------------

    def list_activity_logs(self, user_id=None, resource_type=None, resource_id=None,
                           start_date=None, end_date=None, page_size=25):
        params = {
            "user_id": user_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "start_date": start_date,
            "end_date": end_date,
        }
        return self._paginate("/activity_logs", params, page_size)
