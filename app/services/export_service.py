from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

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
    selected_variant = build_preview_variant(manifest, variant_id=variant_id or manifest.selected_variant_id)
    brief = manifest.brief.to_dict()
    rendered_html = render_template(
        "exported_site.html",
        page_title=brief.get("name") or "VeloSite Export",
        brief=brief,
        selected_variant=selected_variant,
        css_href=css_href,
        consumer_mode=True,
    )
    css_text = EXPORT_CSS_PATH.read_text(encoding="utf-8")
    return rendered_html, css_text, selected_variant


def build_export_bundle(manifest: ProjectManifest) -> tuple[BytesIO, str]:
    rendered_html, css_text, selected_variant = render_export_site(manifest)
    brief = manifest.brief.to_dict()
    timestamp = datetime.now(UTC).isoformat()
    archive_name = _slugify(brief.get("name") or manifest.prompt or manifest.preview_id)

    manifest_json = json.dumps(manifest.to_dict(), indent=2)
    metadata_json = json.dumps(
        {
            "preview_id": manifest.preview_id,
            "exported_at": timestamp,
            "selected_variant_id": manifest.selected_variant_id,
            "template_key": selected_variant["render_plan"]["template_key"],
            "layout_mode": selected_variant["render_plan"]["layout_mode"],
            "art_direction": selected_variant["render_plan"]["art_direction"],
        },
        indent=2,
    )
    readme = "\n".join(
        [
            "VeloSite Export",
            "",
            "Files:",
            "- index.html: exported standalone preview",
            "- manifest.json: full generation manifest",
            "- export-metadata.json: export context",
            "- assets/export-frame.css: frame-level styles",
            "",
            "This export is generated from the deterministic VeloSite preview pipeline.",
        ]
    )

    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("index.html", rendered_html)
        archive.writestr("manifest.json", manifest_json)
        archive.writestr("export-metadata.json", metadata_json)
        archive.writestr("README.txt", readme)
        archive.writestr("assets/export-frame.css", css_text)

    buffer.seek(0)
    return buffer, f"{archive_name}.zip"
