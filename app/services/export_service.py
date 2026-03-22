from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from typing import Callable

from flask import render_template

from app.services.ai_engine import build_preview_variant
from app.services.contracts import ProjectManifest

EXPORT_CSS_PATH = Path(__file__).resolve().parent.parent / "static" / "css" / "export-frame.css"


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "velosite-export"


def render_export_site(
    manifest: ProjectManifest,
    *,
    variant_id: str | None = None,
    css_href: str = "assets/export-frame.css",
) -> tuple[str, str, dict[str, object]]:
    rendered_pages, css_text, selected_variant = render_export_pages(
        manifest,
        variant_id=variant_id,
        css_href=css_href,
    )
    rendered_html = rendered_pages.get("home") or next(iter(rendered_pages.values()), "")
    return rendered_html, css_text, selected_variant


def render_export_pages(
    manifest: ProjectManifest,
    *,
    variant_id: str | None = None,
    css_href: str = "assets/export-frame.css",
    page_href_builder: Callable[[str], str] | None = None,
) -> tuple[dict[str, str], str, dict[str, object]]:
    selected_variant = build_preview_variant(manifest, variant_id=variant_id or manifest.selected_variant_id, page_slug="home")
    brief = manifest.brief.to_dict()
    pages = selected_variant.get("render_plan", {}).get("pages", []) if isinstance(selected_variant.get("render_plan"), dict) else []
    page_slugs = [
        str(page.get("slug", "")).strip()
        for page in pages
        if isinstance(page, dict) and str(page.get("slug", "")).strip()
    ] or ["home"]
    href_builder = page_href_builder or (lambda slug: "index.html" if slug == "home" else f"{slug}.html")
    page_href_map = {slug: href_builder(slug) for slug in page_slugs}
    rendered_pages: dict[str, str] = {}
    for slug in page_slugs:
        page_variant = build_preview_variant(
            manifest,
            variant_id=variant_id or manifest.selected_variant_id,
            page_slug=slug,
        )
        rendered_pages[slug] = render_template(
            "exported_site.html",
            page_title=brief.get("name") or "VeloSite Export",
            brief=brief,
            selected_variant=page_variant,
            css_href=css_href,
            page_href_map=page_href_map,
            consumer_mode=True,
        )
    css_text = EXPORT_CSS_PATH.read_text(encoding="utf-8")
    return rendered_pages, css_text, selected_variant


def _resolved_manifest_payload(manifest: ProjectManifest) -> dict[str, object]:
    payload = manifest.to_dict()
    payload["variants"] = [
        build_preview_variant(manifest, variant_id=variant.variant_id)
        for variant in manifest.variants
    ]
    return payload


def build_export_bundle(manifest: ProjectManifest) -> tuple[BytesIO, str]:
    rendered_pages, css_text, selected_variant = render_export_pages(manifest)
    brief = manifest.brief.to_dict()
    timestamp = datetime.now(UTC).isoformat()
    archive_name = _slugify(brief.get("name") or manifest.prompt or manifest.preview_id)

    manifest_json = json.dumps(_resolved_manifest_payload(manifest), indent=2)
    metadata_json = json.dumps(
        {
            "preview_id": manifest.preview_id,
            "exported_at": timestamp,
            "selected_variant_id": manifest.selected_variant_id,
            "template_key": selected_variant["render_plan"]["template_key"],
            "layout_mode": selected_variant["render_plan"]["layout_mode"],
            "art_direction": selected_variant["render_plan"]["art_direction"],
            "pages": list(rendered_pages.keys()),
        },
        indent=2,
    )
    readme = "\n".join(
        [
            "VeloSite Export",
            "",
            "Files:",
            "- index.html: exported home page",
            "- <page>.html: exported secondary pages",
            "- manifest.json: full generation manifest",
            "- export-metadata.json: export context",
            "- assets/export-frame.css: frame-level styles",
            "",
            "This export is generated from the deterministic VeloSite preview pipeline.",
        ]
    )

    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        for slug, rendered_html in rendered_pages.items():
            archive.writestr("index.html" if slug == "home" else f"{slug}.html", rendered_html)
        archive.writestr("manifest.json", manifest_json)
        archive.writestr("export-metadata.json", metadata_json)
        archive.writestr("README.txt", readme)
        archive.writestr("assets/export-frame.css", css_text)

    buffer.seek(0)
    return buffer, f"{archive_name}.zip"
