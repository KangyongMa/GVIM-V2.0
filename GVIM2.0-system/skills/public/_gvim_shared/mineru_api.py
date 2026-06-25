#!/usr/bin/env python3
"""Shared MinerU API client for GVIM/DeerFlow skills.

Default mode is auto: use MinerU v4 precise API when MINERU_API_TOKEN is set,
otherwise fall back to the token-free Agent API for desktop GVIM deployment.
"""

from __future__ import annotations

import json
import os
import time
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import requests


AGENT_BASE_URL = "https://mineru.net/api/v1/agent"
V4_BASE_URL = "https://mineru.net/api/v4"
AGENT_MAX_BYTES = 10 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 600
DEFAULT_POLL_SECONDS = 3


class MinerUApiError(RuntimeError):
    """Raised when the remote MinerU API cannot finish a parse task."""


def parse_pdf_with_mineru_api(
    pdf_path: str | Path,
    output_dir: str | Path,
    *,
    language: str = "ch",
    page_range: Optional[str] = None,
    enable_table: bool = True,
    is_ocr: bool = False,
    enable_formula: bool = True,
    mode: Optional[str] = None,
    model_version: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
    poll_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    """Parse a local PDF through MinerU API and save a Markdown file locally."""

    selected_mode = (mode or os.getenv("MINERU_API_MODE", "auto")).strip().lower()
    if selected_mode in {"precise", "v4", "standard"}:
        return parse_pdf_with_precise_api(
            pdf_path,
            output_dir,
            language=language,
            page_range=page_range,
            enable_table=enable_table,
            is_ocr=is_ocr,
            enable_formula=enable_formula,
            model_version=model_version,
            timeout_seconds=timeout_seconds,
            poll_seconds=poll_seconds,
        )
    if selected_mode == "auto" and os.getenv("MINERU_API_TOKEN"):
        return parse_pdf_with_precise_api(
            pdf_path,
            output_dir,
            language=language,
            page_range=page_range,
            enable_table=enable_table,
            is_ocr=is_ocr,
            enable_formula=enable_formula,
            model_version=model_version,
            timeout_seconds=timeout_seconds,
            poll_seconds=poll_seconds,
        )
    return parse_pdf_with_agent_api(
        pdf_path,
        output_dir,
        language=language,
        page_range=page_range,
        enable_table=enable_table,
        is_ocr=is_ocr,
        enable_formula=enable_formula,
        timeout_seconds=timeout_seconds,
        poll_seconds=poll_seconds,
    )


def parse_pdf_with_agent_api(
    pdf_path: str | Path,
    output_dir: str | Path,
    *,
    language: str = "ch",
    page_range: Optional[str] = None,
    enable_table: bool = True,
    is_ocr: bool = False,
    enable_formula: bool = True,
    timeout_seconds: Optional[int] = None,
    poll_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    """Parse a local PDF with MinerU Agent API.

    Official limit for this endpoint is 10 MB and 20 pages. It returns Markdown
    links only, which is enough for the existing literature/reaction/DFT skills.
    """

    try:
        input_path = _validate_input_file(pdf_path)
        if input_path.stat().st_size > AGENT_MAX_BYTES:
            return _error(
                "MinerU Agent API limit is 10 MB. Set MINERU_API_MODE=precise "
                "and MINERU_API_TOKEN to use the v4 precise API."
            )

        output_path = Path(output_dir).expanduser().resolve()
        parse_dir = output_path / input_path.stem
        parse_dir.mkdir(parents=True, exist_ok=True)

        base_url = os.getenv("MINERU_AGENT_API_BASE", AGENT_BASE_URL).rstrip("/")
        payload: Dict[str, Any] = {
            "file_name": input_path.name,
            "language": language,
            "enable_table": enable_table,
            "is_ocr": is_ocr,
            "enable_formula": enable_formula,
        }
        if page_range:
            payload["page_range"] = page_range

        created = _post_json(f"{base_url}/parse/file", payload)
        if created.get("code") != 0:
            return _error(f"MinerU Agent task creation failed: {created.get('msg')}", response=created)

        task_id = created.get("data", {}).get("task_id")
        file_url = created.get("data", {}).get("file_url")
        if not task_id or not file_url:
            return _error("MinerU Agent response did not include task_id/file_url.", response=created)

        _upload_file(file_url, input_path)
        final_response = _poll_agent_result(
            base_url,
            task_id,
            timeout_seconds=_timeout_seconds(timeout_seconds),
            poll_seconds=_poll_seconds(poll_seconds),
        )
        data = final_response.get("data", {})
        markdown_url = data.get("markdown_url")
        if not markdown_url:
            return _error("MinerU Agent response did not include markdown_url.", response=final_response)

        markdown_text = _download_text(markdown_url)
        markdown_file = parse_dir / "full.md"
        markdown_file.write_text(markdown_text, encoding="utf-8")
        result_file = parse_dir / "mineru_agent_result.json"
        _write_json(result_file, final_response)

        return {
            "success": True,
            "mode": "agent",
            "input_file": str(input_path),
            "output_dir": str(parse_dir),
            "markdown_file": str(markdown_file),
            "text_content": markdown_text,
            "images_dir": None,
            "images_count": 0,
            "task_id": task_id,
            "markdown_url": markdown_url,
            "raw_result_file": str(result_file),
            "api_response": final_response,
        }
    except Exception as exc:
        return _error(str(exc))


def parse_pdf_with_precise_api(
    pdf_path: str | Path,
    output_dir: str | Path,
    *,
    language: str = "ch",
    page_range: Optional[str] = None,
    enable_table: bool = True,
    is_ocr: bool = False,
    enable_formula: bool = True,
    model_version: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
    poll_seconds: Optional[int] = None,
) -> Dict[str, Any]:
    """Parse a local PDF with MinerU v4 precise API."""

    try:
        token = os.getenv("MINERU_API_TOKEN")
        if not token:
            return _error("MINERU_API_TOKEN is required when MINERU_API_MODE=precise.")

        input_path = _validate_input_file(pdf_path)
        output_path = Path(output_dir).expanduser().resolve()
        parse_dir = output_path / input_path.stem
        parse_dir.mkdir(parents=True, exist_ok=True)

        base_url = os.getenv("MINERU_V4_API_BASE", V4_BASE_URL).rstrip("/")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        file_item: Dict[str, Any] = {"name": input_path.name}
        if page_range:
            file_item["page_ranges"] = page_range
        payload = {
            "files": [file_item],
            "model_version": model_version or os.getenv("MINERU_API_MODEL", "vlm"),
            "language": language,
            "enable_table": enable_table,
            "is_ocr": is_ocr,
            "enable_formula": enable_formula,
        }

        created = _post_json(f"{base_url}/file-urls/batch", payload, headers=headers)
        if created.get("code") != 0:
            return _error(f"MinerU precise task creation failed: {created.get('msg')}", response=created)

        data = created.get("data", {})
        batch_id = data.get("batch_id")
        file_urls = data.get("file_urls") or []
        if not batch_id or not file_urls:
            return _error("MinerU precise response did not include batch_id/file_urls.", response=created)

        _upload_file(_coerce_upload_url(file_urls[0]), input_path)
        final_response, item = _poll_precise_result(
            base_url,
            batch_id,
            headers=headers,
            timeout_seconds=_timeout_seconds(timeout_seconds),
            poll_seconds=_poll_seconds(poll_seconds),
        )
        zip_url = item.get("full_zip_url")
        if not zip_url:
            return _error("MinerU precise response did not include full_zip_url.", response=final_response)

        zip_file = parse_dir / "mineru_result.zip"
        _download_binary(zip_url, zip_file)
        extracted_dir = parse_dir / "extracted"
        extracted_dir.mkdir(parents=True, exist_ok=True)
        _safe_extract_zip(zip_file, extracted_dir)

        markdown_file = _find_markdown_file(extracted_dir)
        if not markdown_file:
            return _error("MinerU precise zip did not contain a Markdown file.", response=final_response)

        markdown_text = markdown_file.read_text(encoding="utf-8", errors="replace")
        result_file = parse_dir / "mineru_precise_result.json"
        _write_json(result_file, final_response)
        images_dir = _find_first_dir(extracted_dir, "images")
        images = _list_images(images_dir) if images_dir else []

        return {
            "success": True,
            "mode": "precise",
            "input_file": str(input_path),
            "output_dir": str(parse_dir),
            "markdown_file": str(markdown_file),
            "text_content": markdown_text,
            "images_dir": str(images_dir) if images_dir else None,
            "images_count": len(images),
            "images": [str(path) for path in images],
            "batch_id": batch_id,
            "full_zip_url": zip_url,
            "raw_result_file": str(result_file),
            "api_response": final_response,
        }
    except Exception as exc:
        return _error(str(exc))


def _poll_agent_result(
    base_url: str,
    task_id: str,
    *,
    timeout_seconds: int,
    poll_seconds: int,
) -> Dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_response: Dict[str, Any] = {}
    while time.monotonic() < deadline:
        last_response = _get_json(f"{base_url}/parse/{task_id}")
        if last_response.get("code") != 0:
            raise MinerUApiError(f"MinerU Agent poll failed: {last_response.get('msg')}")
        data = last_response.get("data", {})
        state = data.get("state")
        if state == "done":
            return last_response
        if state == "failed":
            raise MinerUApiError(data.get("err_msg") or "MinerU Agent task failed.")
        time.sleep(poll_seconds)
    raise MinerUApiError(f"MinerU Agent polling timed out after {timeout_seconds}s. task_id={task_id}")


def _poll_precise_result(
    base_url: str,
    batch_id: str,
    *,
    headers: Dict[str, str],
    timeout_seconds: int,
    poll_seconds: int,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = _get_json(f"{base_url}/extract-results/batch/{batch_id}", headers=headers)
        if response.get("code") != 0:
            raise MinerUApiError(f"MinerU precise poll failed: {response.get('msg')}")
        results = response.get("data", {}).get("extract_result") or []
        if results:
            item = results[0]
            state = item.get("state")
            if state == "done":
                return response, item
            if state == "failed":
                raise MinerUApiError(item.get("err_msg") or "MinerU precise task failed.")
        time.sleep(poll_seconds)
    raise MinerUApiError(f"MinerU precise polling timed out after {timeout_seconds}s. batch_id={batch_id}")


def _validate_input_file(file_path: str | Path) -> Path:
    path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Input file does not exist: {path}")
    if not path.is_file():
        raise ValueError(f"Input path is not a file: {path}")
    return path


def _post_json(url: str, payload: Dict[str, Any], *, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    return _decode_response(response)


def _get_json(url: str, *, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    response = requests.get(url, headers=headers, timeout=60)
    return _decode_response(response)


def _decode_response(response: requests.Response) -> Dict[str, Any]:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise MinerUApiError(f"HTTP {response.status_code}: {response.text[:500]}") from exc
    try:
        return response.json()
    except ValueError as exc:
        raise MinerUApiError(f"Response is not JSON: {response.text[:500]}") from exc


def _upload_file(file_url: str, input_path: Path, *, content_type: Optional[str] = None) -> None:
    headers = {"Content-Type": content_type} if content_type else None
    with input_path.open("rb") as stream:
        response = requests.put(file_url, data=stream, headers=headers, timeout=300)
    if response.status_code not in {200, 201}:
        raise MinerUApiError(f"File upload failed with HTTP {response.status_code}: {response.text[:500]}")


def _download_text(url: str) -> str:
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    response.encoding = response.encoding or "utf-8"
    return response.text


def _download_binary(url: str, output_file: Path) -> None:
    with requests.get(url, stream=True, timeout=300) as response:
        response.raise_for_status()
        with output_file.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)


def _safe_extract_zip(zip_file: Path, target_dir: Path) -> None:
    target_root = target_dir.resolve()
    with zipfile.ZipFile(zip_file) as archive:
        for member in archive.infolist():
            member_path = (target_root / member.filename).resolve()
            try:
                member_path.relative_to(target_root)
            except ValueError as exc:
                raise MinerUApiError(f"Unsafe zip member path: {member.filename}")
        archive.extractall(target_root)


def _coerce_upload_url(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("url", "file_url", "upload_url"):
            if value.get(key):
                return str(value[key])
    raise MinerUApiError(f"Unexpected upload URL value: {value!r}")


def _find_markdown_file(root: Path) -> Optional[Path]:
    full_md = list(root.rglob("full.md"))
    if full_md:
        return full_md[0]
    md_files = list(root.rglob("*.md"))
    return md_files[0] if md_files else None


def _find_first_dir(root: Path, name: str) -> Optional[Path]:
    for path in root.rglob(name):
        if path.is_dir():
            return path
    return None


def _list_images(root: Optional[Path]) -> list[Path]:
    if not root:
        return []
    suffixes = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
    return [path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in suffixes]


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _timeout_seconds(value: Optional[int]) -> int:
    return int(value or os.getenv("MINERU_API_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))


def _poll_seconds(value: Optional[int]) -> int:
    return int(value or os.getenv("MINERU_API_POLL_SECONDS", DEFAULT_POLL_SECONDS))


def _error(message: str, **extra: Any) -> Dict[str, Any]:
    result: Dict[str, Any] = {"success": False, "error": message}
    result.update(extra)
    return result
