from __future__ import annotations

import base64
from typing import Any
from urllib.parse import quote

import requests

from code_validator.github.models import CommitSummary


class GitHubClient:
    def __init__(self, token: str, api_url: str = "https://api.github.com") -> None:
        self._api_url = api_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        if token:
            self._session.headers["Authorization"] = f"Bearer {token}"

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        response = self._session.get(f"{self._api_url}{path}", params=params, timeout=20)
        response.raise_for_status()
        return response.json()

    def get_latest_commit(self, repo: str, branch: str) -> CommitSummary:
        
        encoded_branch = quote(branch, safe="")
        data = self._get(f"/repos/{repo}/commits/{encoded_branch}")
        return CommitSummary(
            sha=data["sha"],
            tree_sha=((data.get("commit") or {}).get("tree") or {}).get("sha", ""),
            author_login=(data.get("author") or {}).get("login"),
            author_email=((data.get("commit") or {}).get("author") or {}).get("email"),
        )

    def list_repository_files(self, repo: str, tree_sha: str) -> list[str]:
        data = self._get(f"/repos/{repo}/git/trees/{tree_sha}", params={"recursive": "1"})
        items = data.get("tree", [])
        return [item["path"] for item in items if item.get("type") == "blob"]

    def get_file_content(self, repo: str, path: str, sha: str) -> str:
        
        encoded_path = quote(path, safe="/")
        data = self._get(f"/repos/{repo}/contents/{encoded_path}", params={"ref": sha})
        encoding = data.get("encoding")
        if encoding == "base64":
            encoded = data.get("content", "")
            return base64.b64decode(encoded).decode("utf-8", errors="replace")
        download_url = data.get("download_url")
        if download_url:
            response = self._session.get(download_url, timeout=20)
            response.raise_for_status()
            return response.text
        content = data.get("content")
        if content is None:
            return ""
        return str(content)

    def is_org_member(self, org: str, username: str) -> bool:
        response = self._session.get(
            f"{self._api_url}/orgs/{org}/members/{username}",
            timeout=20,
        )
        if response.status_code == 204:
            return True
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return False
