from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from flask import render_template

from app.services.contracts import ProjectManifest

EXPORT_CSS_PATH = Path(__file__).resolve().parent.parent / "static" / "css" / "export-frame.css"


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "velosite-export"


def build_export_bundle(manifest: ProjectManifest) -> tuple[BytesIO, str]:
    selected_variant = next(
        (variant for variant in manifest.variants if variant.variant_id == manifest.selected_variant_id),
        manifest.variants[0],
    )
    brief = manifest.brief.to_dict()
    rendered_html = render_template(
        "exported_site.html",
        page_title=brief.get("name") or "VeloSite Export",
        brief=brief,
        selected_variant=selected_variant.to_dict(),
    )
    css_text = EXPORT_CSS_PATH.read_text(encoding="utf-8")
    timestamp = datetime.now(UTC).isoformat()
    archive_name = _slugify(brief.get("name") or manifest.prompt or manifest.preview_id)

    manifest_json = json.dumps(manifest.to_dict(), indent=2)
    metadata_json = json.dumps(
        {
            "preview_id": manifest.preview_id,
            "exported_at": timestamp,
            "selected_variant_id": manifest.selected_variant_id,
            "template_key": selected_variant.render_plan.template_key,
            "layout_mode": selected_variant.render_plan.layout_mode,
            "art_direction": selected_variant.render_plan.art_direction,
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
