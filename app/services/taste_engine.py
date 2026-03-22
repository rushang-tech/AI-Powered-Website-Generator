from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field, replace
from typing import Any


DEFAULT_TEMPLATE_SIGNALS: dict[str, dict[str, tuple[str, ...]]] = {
    "store": {
        "phrases": (
            "online store",
            "ecommerce store",
            "shopify store",
            "product catalog",
            "collection page",
            "shopping website",
        ),
        "strong_terms": (
            "store",
            "shop",
            "ecommerce",
            "catalog",
            "collection",
            "retail",
            "merch",
            "product",
            "products",
        ),
        "support_terms": (
            "sale",
            "browse",
            "buy",
            "drop",
            "inventory",
            "checkout",
            "featured",
            "shop-now",
        ),
    },
    "saas": {
        "phrases": (
            "saas landing page",
            "software website",
            "ai copilot",
            "app landing page",
            "product marketing page",
            "software launch page",
        ),
        "strong_terms": (
            "saas",
            "software",
            "copilot",
            "platform",
            "app",
            "dashboard",
            "workflow",
            "automation",
            "workspace",
        ),
        "support_terms": (
            "demo",
            "trial",
            "integration",
            "analytics",
            "team",
            "ai",
            "product",
            "release",
        ),
    },
    "landing": {
        "phrases": (
            "landing page",
            "marketing page",
            "campaign page",
            "lead generation",
            "waitlist page",
            "event page",
        ),
        "strong_terms": (
            "landing",
            "startup",
            "agency",
            "service",
            "business",
            "brand",
            "campaign",
            "conversion",
            "book",
            "appointment",
        ),
        "support_terms": (
            "company",
            "audience",
            "offer",
            "growth",
            "lead",
            "cta",
            "headline",
        ),
    },
    "portfolio": {
        "phrases": (
            "personal website",
            "case study",
            "case studies",
            "my portfolio",
            "about me",
        ),
        "strong_terms": (
            "portfolio",
            "resume",
            "cv",
            "designer",
            "developer",
            "photographer",
            "artist",
            "freelance",
            "freelancer",
            "showcase",
        ),
        "support_terms": (
            "projects",
            "experience",
            "work",
            "skills",
            "bio",
            "profile",
        ),
    },
    "business": {
        "phrases": (
            "business website",
            "company website",
            "service business",
            "agency website",
            "local business website",
        ),
        "strong_terms": (
            "business",
            "company",
            "agency",
            "service",
            "services",
            "consulting",
            "firm",
            "clinic",
            "restaurant",
            "hotel",
            "salon",
        ),
        "support_terms": (
            "team",
            "book",
            "appointment",
            "location",
            "contact",
            "trust",
            "review",
            "process",
        ),
    },
    "product": {
        "phrases": (
            "product launch",
            "pricing page",
            "online store",
            "ecommerce store",
            "saas product",
            "app landing",
        ),
        "strong_terms": (
            "product",
            "store",
            "shop",
            "ecommerce",
            "saas",
            "app",
            "pricing",
            "subscription",
            "checkout",
            "trial",
        ),
        "support_terms": (
            "launch",
            "feature",
            "features",
            "plan",
            "plans",
            "demo",
            "growth",
            "retention",
        ),
    },
}

ART_DIRECTION_SIGNALS: dict[str, dict[str, tuple[str, ...]]] = {
    "modern_editorial": {
        "phrases": ("clean layout", "minimal style", "professional look", "editorial look"),
        "strong_terms": ("clean", "minimal", "professional", "simple", "sleek", "editorial"),
        "support_terms": ("balanced", "structured", "neutral", "refined", "b2b"),
    },
    "luxury_serif": {
        "phrases": ("premium feel", "high end", "editorial luxury", "quiet luxury"),
        "strong_terms": ("premium", "elegant", "luxury", "exclusive", "refined", "timeless"),
        "support_terms": ("polished", "crafted", "serif", "soft", "rich"),
    },
    "playful_blocks": {
        "phrases": ("kid friendly", "children friendly", "fun vibe", "bright colors"),
        "strong_terms": ("fun", "colorful", "friendly", "quirky", "vibrant", "playful"),
        "support_terms": ("kids", "children", "joyful", "bold", "cartoon"),
    },
    "cyber_signal": {
        "phrases": ("futuristic neon", "sci fi", "tech noir", "hacker vibe"),
        "strong_terms": ("neon", "futuristic", "cyber", "cyberpunk", "glow", "techno"),
        "support_terms": ("matrix", "electric", "night", "gaming", "hologram"),
    },
    "brutalist_poster": {
        "phrases": ("poster style", "raw design", "graphic design system"),
        "strong_terms": ("brutalist", "poster", "graphic", "raw", "sharp", "experimental"),
        "support_terms": ("loud", "contrast", "angular", "bold", "print"),
    },
    "warm_gradient": {
        "phrases": ("warm gradient", "soft startup", "friendly tech"),
        "strong_terms": ("warm", "gradient", "sunset", "approachable", "optimistic"),
        "support_terms": ("soft", "welcoming", "uplifting", "bright", "human"),
    },
    "coastal_breeze": {
        "phrases": ("coastal calm", "ocean inspired", "resort modern", "airy blue"),
        "strong_terms": ("coastal", "ocean", "sea", "breeze", "fresh", "airy"),
        "support_terms": ("travel", "resort", "spa", "light", "blue"),
    },
    "mono_signal": {
        "phrases": ("swiss poster", "monochrome system", "black and white", "high contrast minimal"),
        "strong_terms": ("monochrome", "swiss", "grid", "minimalist", "black", "white"),
        "support_terms": ("contrast", "signal", "precise", "sharp", "modernist"),
    },
    "botanical_noir": {
        "phrases": ("organic luxury", "botanical premium", "earthy dark", "natural editorial"),
        "strong_terms": ("botanical", "organic", "forest", "earthy", "natural", "verdant"),
        "support_terms": ("calm", "wellness", "garden", "serene", "crafted"),
    },
    "studio_pop": {
        "phrases": ("art school poster", "studio color", "expressive editorial", "creative pop"),
        "strong_terms": ("expressive", "graphic", "electric", "cobalt", "creative", "pop"),
        "support_terms": ("studio", "magazine", "dynamic", "vivid", "experimental"),
    },
}

TEMPLATE_ART_DIRECTION_BIASES: dict[str, tuple[str, ...]] = {
    "store": ("luxury_serif", "warm_gradient", "modern_editorial"),
    "saas": ("cyber_signal", "mono_signal", "modern_editorial"),
    "landing": ("warm_gradient", "modern_editorial", "mono_signal"),
    "portfolio": ("brutalist_poster", "studio_pop", "luxury_serif"),
    "business": ("modern_editorial", "warm_gradient", "coastal_breeze"),
    "product": ("cyber_signal", "mono_signal", "luxury_serif"),
}

PRIMARY_TEMPLATE_KEYS = ("store", "saas", "portfolio", "business")
PRIMARY_VARIANT_LAYOUTS: dict[str, tuple[str, ...]] = {
    "store": ("editorial_lookbook", "conversion_storefront", "catalog_first"),
    "saas": ("product_story", "dashboard_proof", "workflow_first"),
    "portfolio": ("casebook_editorial", "gallery_wall", "minimal_identity"),
    "business": ("service_story", "trust_first", "offer_stack"),
}

ART_DIRECTION_INDUSTRY_BIASES: dict[str, tuple[str, ...]] = {
    "fitness": ("playful_blocks", "warm_gradient", "brutalist_poster"),
    "technology": ("cyber_signal", "mono_signal", "modern_editorial"),
    "retail": ("warm_gradient", "luxury_serif", "playful_blocks"),
    "creative": ("brutalist_poster", "studio_pop", "playful_blocks"),
    "finance": ("mono_signal", "luxury_serif", "modern_editorial"),
    "healthcare": ("warm_gradient", "modern_editorial", "luxury_serif"),
    "education": ("playful_blocks", "warm_gradient", "modern_editorial"),
    "hospitality": ("coastal_breeze", "warm_gradient", "luxury_serif"),
    "music": ("studio_pop", "brutalist_poster", "cyber_signal"),
    "real_estate": ("luxury_serif", "modern_editorial", "warm_gradient"),
    "wellness": ("botanical_noir", "warm_gradient", "coastal_breeze"),
}

ART_DIRECTION_VIBE_BIASES: dict[str, tuple[str, ...]] = {
    "minimal": ("modern_editorial", "mono_signal", "coastal_breeze"),
    "bold": ("brutalist_poster", "studio_pop", "cyber_signal"),
    "playful": ("playful_blocks", "warm_gradient", "brutalist_poster"),
    "premium": ("luxury_serif", "botanical_noir", "modern_editorial"),
    "futuristic": ("cyber_signal", "mono_signal", "modern_editorial"),
    "warm": ("warm_gradient", "botanical_noir", "playful_blocks"),
}

ART_DIRECTION_TRAITS: dict[str, dict[str, str]] = {
    "modern_editorial": {"family": "editorial", "temperature": "neutral", "contrast": "medium", "energy": "calm"},
    "luxury_serif": {"family": "heritage", "temperature": "warm", "contrast": "soft", "energy": "calm"},
    "playful_blocks": {"family": "playful", "temperature": "mixed", "contrast": "high", "energy": "lively"},
    "cyber_signal": {"family": "tech_noir", "temperature": "cool", "contrast": "high", "energy": "high"},
    "brutalist_poster": {"family": "poster", "temperature": "neutral", "contrast": "high", "energy": "high"},
    "warm_gradient": {"family": "sunset", "temperature": "warm", "contrast": "soft", "energy": "calm"},
    "coastal_breeze": {"family": "coastal", "temperature": "cool", "contrast": "soft", "energy": "calm"},
    "mono_signal": {"family": "monochrome", "temperature": "neutral", "contrast": "high", "energy": "calm"},
    "botanical_noir": {"family": "botanical", "temperature": "earth", "contrast": "medium", "energy": "calm"},
    "studio_pop": {"family": "studio", "temperature": "warm", "contrast": "high", "energy": "high"},
}

INDUSTRY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "fitness": ("fitness", "gym", "workout", "yoga", "coach"),
    "technology": ("tech", "ai", "saas", "software", "app", "developer"),
    "retail": (
        "shop",
        "store",
        "product",
        "ecommerce",
        "fashion",
        "bakery",
        "bakehouse",
        "pastry",
        "bread",
        "cake",
        "dessert",
        "cafe",
        "coffee",
        "restaurant",
        "menu",
        "food",
    ),
    "creative": ("designer", "artist", "photography", "portfolio", "studio"),
    "finance": ("finance", "bank", "investment", "fintech", "accounting"),
    "healthcare": ("health", "clinic", "medical", "wellness", "doctor"),
    "education": ("education", "academy", "course", "lesson", "learning", "school", "class", "workshop", "bootcamp"),
    "hospitality": ("hotel", "resort", "travel", "restaurant", "cafe", "bar", "booking", "venue", "stay"),
    "music": ("music", "band", "album", "dj", "festival", "tour", "record", "label", "audio"),
    "real_estate": ("real estate", "property", "realtor", "listing", "home", "apartment", "condo", "broker"),
    "wellness": ("spa", "salon", "beauty", "massage", "mindfulness", "skincare", "wellness", "self-care"),
}

VIBE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "minimal": ("minimal", "clean", "simple"),
    "bold": ("bold", "loud", "strong", "poster"),
    "playful": ("playful", "fun", "friendly", "quirky"),
    "premium": ("luxury", "premium", "exclusive", "elegant"),
    "futuristic": ("futuristic", "cyber", "neon", "techno"),
    "warm": ("warm", "approachable", "soft", "friendly"),
}

DENSITY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "airy": ("airy", "minimal", "breathing", "spacious", "light"),
    "balanced": ("balanced", "clear", "focused", "structured"),
    "dense": ("dense", "information", "detailed", "rich", "packed"),
}

MOTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "calm": ("calm", "quiet", "subtle", "steady", "slow"),
    "moderate": ("dynamic", "lively", "animated", "interactive"),
    "energetic": ("energetic", "fast", "bold", "kinetic", "immersive"),
}

STOPWORDS = {
    "a",
    "an",
    "the",
    "for",
    "with",
    "and",
    "that",
    "this",
    "from",
    "your",
    "our",
    "into",
    "like",
    "need",
    "build",
    "make",
    "website",
    "page",
    "site",
}

ALLOWED_BRAND_ASSET_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    "image/svg+xml",
}

MAX_BRAND_ASSETS = 4
MAX_BRAND_ASSET_NAME_LENGTH = 80
MAX_BRAND_ASSET_ALT_LENGTH = 140
MAX_BRAND_ASSET_DATA_URL_LENGTH = 1_800_000

NAVIGATION_PATTERNS: tuple[str, ...] = (
    "brand_left_masthead",
    "centered_editorial_bar",
    "split_utility_header",
    "framed_sidebar_nav",
)

SECTION_LABELS: dict[str, str] = {
    "hero": "Home",
    "metrics": "Results",
    "features": "Highlights",
    "projects": "Work",
    "pricing": "Pricing",
    "proof": "Reviews",
    "cta": "Contact",
    "about": "About",
    "capabilities": "Services",
    "collections": "Collections",
    "products": "Products",
    "workflows": "Workflows",
    "services": "Services",
    "process": "Process",
}

TEMPLATE_PAGE_BLUEPRINTS: dict[str, list[dict[str, Any]]] = {
    "store": [
        {"slug": "collections", "label": "Collections", "page_role": "catalog"},
        {"slug": "products", "label": "Products", "page_role": "catalog"},
        {"slug": "reviews", "label": "Reviews", "page_role": "proof"},
        {"slug": "contact", "label": "Contact", "page_role": "contact"},
    ],
    "saas": [
        {"slug": "workflows", "label": "Workflows", "page_role": "workflow"},
        {"slug": "features", "label": "Features", "page_role": "features"},
        {"slug": "pricing", "label": "Pricing", "page_role": "pricing"},
        {"slug": "contact", "label": "Contact", "page_role": "contact"},
    ],
    "business": [
        {"slug": "services", "label": "Services", "page_role": "services"},
        {"slug": "process", "label": "Process", "page_role": "process"},
        {"slug": "reviews", "label": "Reviews", "page_role": "proof"},
        {"slug": "contact", "label": "Contact", "page_role": "contact"},
    ],
    "portfolio": [
        {"slug": "projects", "label": "Projects", "page_role": "projects"},
        {"slug": "about", "label": "About", "page_role": "about"},
        {"slug": "capabilities", "label": "Capabilities", "page_role": "capabilities"},
        {"slug": "contact", "label": "Contact", "page_role": "contact"},
    ],
    "landing": [
        {"slug": "features", "label": "Features", "page_role": "features"},
        {"slug": "proof", "label": "Proof", "page_role": "proof"},
        {"slug": "contact", "label": "Contact", "page_role": "contact"},
    ],
    "product": [
        {"slug": "pricing", "label": "Pricing", "page_role": "pricing"},
        {"slug": "features", "label": "Features", "page_role": "features"},
        {"slug": "proof", "label": "Proof", "page_role": "proof"},
        {"slug": "contact", "label": "Contact", "page_role": "contact"},
    ],
}


def _structure_recipe(
    template_key: str,
    *,
    hero_variant: str,
    section_order: list[str],
    keywords: tuple[str, ...],
    density_bias: str,
    motion_bias: str,
    page_shell: str,
    navigation_modes: tuple[str, ...],
    default_navigation_mode: str | None = None,
    promoted_sections: dict[str, list[str]] | None = None,
    section_treatment_keys: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "hero_variant": hero_variant,
        "section_order": section_order,
        "keywords": keywords,
        "density_bias": density_bias,
        "motion_bias": motion_bias,
        "page_shell": page_shell,
        "navigation_modes": list(navigation_modes),
        "default_navigation_mode": default_navigation_mode or navigation_modes[0],
        "default_page_map": [item["slug"] for item in TEMPLATE_PAGE_BLUEPRINTS.get(template_key, [])],
        "promoted_sections": promoted_sections or {},
        "section_treatment_keys": section_treatment_keys or {},
    }


LAYOUT_LIBRARY: dict[str, dict[str, dict[str, Any]]] = {
    "store": {
        "editorial_lookbook": _structure_recipe(
            "store",
            hero_variant="lookbook",
            section_order=["hero", "collections", "products", "proof", "cta"],
            keywords=("editorial", "lookbook", "collection", "story"),
            density_bias="airy",
            motion_bias="moderate",
            page_shell="editorial_frame",
            navigation_modes=("centered_editorial_bar", "brand_left_masthead", "framed_sidebar_nav"),
            default_navigation_mode="centered_editorial_bar",
            promoted_sections={
                "collections": ["collections"],
                "products": ["products"],
                "reviews": ["proof"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "immersive_story",
                "collections": "editorial_cards",
                "products": "product_grid",
                "proof": "testimonial_band",
                "cta": "contact_prompt",
            },
        ),
        "conversion_storefront": _structure_recipe(
            "store",
            hero_variant="storefront",
            section_order=["hero", "products", "proof", "collections", "cta"],
            keywords=("storefront", "conversion", "featured", "buy"),
            density_bias="balanced",
            motion_bias="moderate",
            page_shell="commerce_canvas",
            navigation_modes=("brand_left_masthead", "split_utility_header", "centered_editorial_bar"),
            default_navigation_mode="brand_left_masthead",
            promoted_sections={
                "collections": ["collections"],
                "products": ["products"],
                "reviews": ["proof"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "featured_offer",
                "products": "conversion_grid",
                "collections": "collection_stack",
                "proof": "trust_strip",
                "cta": "checkout_prompt",
            },
        ),
        "catalog_first": _structure_recipe(
            "store",
            hero_variant="catalog",
            section_order=["hero", "products", "collections", "proof", "cta"],
            keywords=("catalog", "browse", "grid", "products"),
            density_bias="dense",
            motion_bias="calm",
            page_shell="catalog_stack",
            navigation_modes=("split_utility_header", "brand_left_masthead", "framed_sidebar_nav"),
            default_navigation_mode="split_utility_header",
            promoted_sections={
                "collections": ["collections"],
                "products": ["products"],
                "reviews": ["proof"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "catalog_intro",
                "products": "catalog_grid",
                "collections": "supporting_collections",
                "proof": "review_tiles",
                "cta": "purchase_prompt",
            },
        ),
    },
    "saas": {
        "product_story": _structure_recipe(
            "saas",
            hero_variant="story",
            section_order=["hero", "features", "workflows", "proof", "pricing", "cta"],
            keywords=("product", "story", "launch", "narrative"),
            density_bias="balanced",
            motion_bias="moderate",
            page_shell="product_storyframe",
            navigation_modes=("split_utility_header", "brand_left_masthead", "centered_editorial_bar"),
            default_navigation_mode="split_utility_header",
            promoted_sections={
                "workflows": ["workflows"],
                "features": ["features"],
                "pricing": ["pricing"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "product_intro",
                "features": "feature_cards",
                "workflows": "workflow_scenes",
                "proof": "proof_strip",
                "pricing": "plan_cards",
                "cta": "trial_prompt",
            },
        ),
        "dashboard_proof": _structure_recipe(
            "saas",
            hero_variant="dashboard",
            section_order=["hero", "proof", "workflows", "features", "pricing", "cta"],
            keywords=("dashboard", "proof", "metrics", "analytics"),
            density_bias="balanced",
            motion_bias="calm",
            page_shell="evidence_shell",
            navigation_modes=("brand_left_masthead", "framed_sidebar_nav", "split_utility_header"),
            default_navigation_mode="framed_sidebar_nav",
            promoted_sections={
                "workflows": ["workflows"],
                "features": ["features"],
                "pricing": ["pricing"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "dashboard_lead",
                "proof": "evidence_block",
                "workflows": "workflow_grid",
                "features": "supporting_features",
                "pricing": "offer_stack",
                "cta": "contact_prompt",
            },
        ),
        "workflow_first": _structure_recipe(
            "saas",
            hero_variant="workflow",
            section_order=["hero", "workflows", "features", "pricing", "proof", "cta"],
            keywords=("workflow", "automation", "process", "product"),
            density_bias="airy",
            motion_bias="moderate",
            page_shell="workflow_shell",
            navigation_modes=("framed_sidebar_nav", "split_utility_header", "centered_editorial_bar"),
            default_navigation_mode="framed_sidebar_nav",
            promoted_sections={
                "workflows": ["workflows"],
                "features": ["features"],
                "pricing": ["pricing"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "workflow_intro",
                "workflows": "workflow_focus",
                "features": "feature_support",
                "pricing": "pricing_compare",
                "proof": "customer_proof",
                "cta": "trial_prompt",
            },
        ),
    },
    "business": {
        "service_story": _structure_recipe(
            "business",
            hero_variant="service",
            section_order=["hero", "services", "process", "proof", "cta"],
            keywords=("service", "offer", "story", "company"),
            density_bias="balanced",
            motion_bias="calm",
            page_shell="service_story_shell",
            navigation_modes=("brand_left_masthead", "centered_editorial_bar", "split_utility_header"),
            default_navigation_mode="brand_left_masthead",
            promoted_sections={
                "services": ["services"],
                "process": ["process"],
                "reviews": ["proof"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "service_intro",
                "services": "offer_cards",
                "process": "process_sequence",
                "proof": "trust_quote",
                "cta": "booking_prompt",
            },
        ),
        "trust_first": _structure_recipe(
            "business",
            hero_variant="trust",
            section_order=["proof", "hero", "services", "process", "cta"],
            keywords=("trust", "reviews", "credibility", "proof"),
            density_bias="balanced",
            motion_bias="calm",
            page_shell="trust_shell",
            navigation_modes=("centered_editorial_bar", "brand_left_masthead", "framed_sidebar_nav"),
            default_navigation_mode="centered_editorial_bar",
            promoted_sections={
                "services": ["services"],
                "process": ["process"],
                "reviews": ["proof"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "proof": "credibility_intro",
                "hero": "service_statement",
                "services": "service_cards",
                "process": "delivery_steps",
                "cta": "contact_prompt",
            },
        ),
        "offer_stack": _structure_recipe(
            "business",
            hero_variant="stack",
            section_order=["hero", "services", "proof", "process", "cta"],
            keywords=("offer", "services", "stack", "clarity"),
            density_bias="dense",
            motion_bias="moderate",
            page_shell="offer_stack_shell",
            navigation_modes=("split_utility_header", "brand_left_masthead", "centered_editorial_bar"),
            default_navigation_mode="split_utility_header",
            promoted_sections={
                "services": ["services"],
                "process": ["process"],
                "reviews": ["proof"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "offer_lead",
                "services": "offer_stack",
                "proof": "review_band",
                "process": "process_cards",
                "cta": "booking_prompt",
            },
        ),
    },
    "landing": {
        "split_hero": _structure_recipe(
            "landing",
            hero_variant="split",
            section_order=["hero", "metrics", "features", "proof", "cta"],
            keywords=("split", "conversion", "clarity", "editorial"),
            density_bias="balanced",
            motion_bias="moderate",
            page_shell="campaign_shell",
            navigation_modes=("brand_left_masthead", "centered_editorial_bar", "split_utility_header"),
            default_navigation_mode="brand_left_masthead",
            promoted_sections={
                "features": ["features", "metrics"],
                "proof": ["proof"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "statement_split",
                "metrics": "result_strip",
                "features": "feature_grid",
                "proof": "testimonial_band",
                "cta": "contact_prompt",
            },
        ),
        "staggered_bands": _structure_recipe(
            "landing",
            hero_variant="banded",
            section_order=["hero", "features", "metrics", "cta"],
            keywords=("campaign", "service", "story", "sectioned"),
            density_bias="balanced",
            motion_bias="calm",
            page_shell="banded_shell",
            navigation_modes=("centered_editorial_bar", "brand_left_masthead", "framed_sidebar_nav"),
            default_navigation_mode="centered_editorial_bar",
            promoted_sections={
                "features": ["features", "metrics"],
                "proof": ["proof"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "campaign_intro",
                "features": "staggered_features",
                "metrics": "supporting_metrics",
                "cta": "contact_prompt",
            },
        ),
        "immersive_layers": _structure_recipe(
            "landing",
            hero_variant="immersive",
            section_order=["hero", "proof", "features", "cta"],
            keywords=("immersive", "layered", "visual", "launch"),
            density_bias="airy",
            motion_bias="energetic",
            page_shell="immersive_shell",
            navigation_modes=("framed_sidebar_nav", "centered_editorial_bar", "split_utility_header"),
            default_navigation_mode="framed_sidebar_nav",
            promoted_sections={
                "features": ["features", "metrics"],
                "proof": ["proof"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "immersive_hero",
                "proof": "early_proof",
                "features": "feature_layers",
                "cta": "contact_prompt",
            },
        ),
        "proof_first": _structure_recipe(
            "landing",
            hero_variant="statement",
            section_order=["proof", "hero", "features", "cta"],
            keywords=("trust", "proof", "testimonial", "credibility"),
            density_bias="dense",
            motion_bias="calm",
            page_shell="proof_shell",
            navigation_modes=("split_utility_header", "brand_left_masthead", "centered_editorial_bar"),
            default_navigation_mode="split_utility_header",
            promoted_sections={
                "features": ["features", "metrics"],
                "proof": ["proof"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "proof": "lead_proof",
                "hero": "hero_after_proof",
                "features": "support_features",
                "cta": "contact_prompt",
            },
        ),
    },
    "portfolio": {
        "casebook_editorial": _structure_recipe(
            "portfolio",
            hero_variant="editorial",
            section_order=["hero", "projects", "about", "proof", "cta"],
            keywords=("casebook", "editorial", "curated", "story"),
            density_bias="balanced",
            motion_bias="calm",
            page_shell="casebook_shell",
            navigation_modes=("centered_editorial_bar", "framed_sidebar_nav", "brand_left_masthead"),
            default_navigation_mode="centered_editorial_bar",
            promoted_sections={
                "projects": ["projects"],
                "about": ["about"],
                "capabilities": ["capabilities"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "editorial_intro",
                "projects": "case_studies",
                "about": "practice_note",
                "proof": "testimonial_quote",
                "cta": "contact_prompt",
            },
        ),
        "gallery_wall": _structure_recipe(
            "portfolio",
            hero_variant="gallery",
            section_order=["hero", "projects", "capabilities", "cta"],
            keywords=("gallery", "wall", "visual", "showcase"),
            density_bias="airy",
            motion_bias="moderate",
            page_shell="gallery_shell",
            navigation_modes=("framed_sidebar_nav", "centered_editorial_bar", "split_utility_header"),
            default_navigation_mode="framed_sidebar_nav",
            promoted_sections={
                "projects": ["projects"],
                "about": ["about"],
                "capabilities": ["capabilities"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "gallery_intro",
                "projects": "masonry_gallery",
                "capabilities": "support_capabilities",
                "cta": "contact_prompt",
            },
        ),
        "minimal_identity": _structure_recipe(
            "portfolio",
            hero_variant="identity",
            section_order=["hero", "about", "capabilities", "projects", "cta"],
            keywords=("minimal", "identity", "resume", "practice"),
            density_bias="dense",
            motion_bias="calm",
            page_shell="identity_shell",
            navigation_modes=("brand_left_masthead", "split_utility_header", "centered_editorial_bar"),
            default_navigation_mode="brand_left_masthead",
            promoted_sections={
                "projects": ["projects"],
                "about": ["about"],
                "capabilities": ["capabilities"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "identity_intro",
                "about": "bio_statement",
                "capabilities": "resume_capabilities",
                "projects": "selected_work",
                "cta": "contact_prompt",
            },
        ),
        "editorial_casebook": _structure_recipe(
            "portfolio",
            hero_variant="editorial",
            section_order=["hero", "projects", "about", "proof", "cta"],
            keywords=("editorial", "case study", "story", "curated"),
            density_bias="balanced",
            motion_bias="calm",
            page_shell="editorial_shell",
            navigation_modes=("centered_editorial_bar", "split_utility_header", "brand_left_masthead"),
            default_navigation_mode="centered_editorial_bar",
            promoted_sections={
                "projects": ["projects"],
                "about": ["about"],
                "capabilities": ["capabilities"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "casebook_intro",
                "projects": "editorial_projects",
                "about": "studio_note",
                "proof": "review_quote",
                "cta": "contact_prompt",
            },
        ),
        "masonry_showcase": _structure_recipe(
            "portfolio",
            hero_variant="gallery",
            section_order=["hero", "projects", "capabilities", "cta"],
            keywords=("showcase", "gallery", "visual", "masonry"),
            density_bias="airy",
            motion_bias="moderate",
            page_shell="showcase_shell",
            navigation_modes=("framed_sidebar_nav", "centered_editorial_bar", "brand_left_masthead"),
            default_navigation_mode="framed_sidebar_nav",
            promoted_sections={
                "projects": ["projects"],
                "about": ["about"],
                "capabilities": ["capabilities"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "showcase_intro",
                "projects": "masonry_showcase",
                "capabilities": "support_capabilities",
                "cta": "contact_prompt",
            },
        ),
        "minimal_cv": _structure_recipe(
            "portfolio",
            hero_variant="resume",
            section_order=["hero", "about", "capabilities", "projects", "cta"],
            keywords=("resume", "cv", "professional", "clean"),
            density_bias="dense",
            motion_bias="calm",
            page_shell="cv_shell",
            navigation_modes=("split_utility_header", "brand_left_masthead", "centered_editorial_bar"),
            default_navigation_mode="split_utility_header",
            promoted_sections={
                "projects": ["projects"],
                "about": ["about"],
                "capabilities": ["capabilities"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "cv_intro",
                "about": "bio_summary",
                "capabilities": "capability_list",
                "projects": "selected_samples",
                "cta": "contact_prompt",
            },
        ),
        "story_panels": _structure_recipe(
            "portfolio",
            hero_variant="panels",
            section_order=["hero", "proof", "projects", "about", "cta"],
            keywords=("panels", "narrative", "story", "sequence"),
            density_bias="balanced",
            motion_bias="moderate",
            page_shell="story_shell",
            navigation_modes=("centered_editorial_bar", "framed_sidebar_nav", "split_utility_header"),
            default_navigation_mode="centered_editorial_bar",
            promoted_sections={
                "projects": ["projects"],
                "about": ["about"],
                "capabilities": ["capabilities"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "story_intro",
                "proof": "lead_quote",
                "projects": "project_panels",
                "about": "practice_note",
                "cta": "contact_prompt",
            },
        ),
    },
    "product": {
        "pricing_first": _structure_recipe(
            "product",
            hero_variant="pricing",
            section_order=["hero", "pricing", "features", "proof", "cta"],
            keywords=("pricing", "plans", "subscription", "trial"),
            density_bias="dense",
            motion_bias="calm",
            page_shell="pricing_shell",
            navigation_modes=("split_utility_header", "brand_left_masthead", "centered_editorial_bar"),
            default_navigation_mode="split_utility_header",
            promoted_sections={
                "pricing": ["pricing"],
                "features": ["features", "metrics"],
                "proof": ["proof"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "pricing_intro",
                "pricing": "pricing_compare",
                "features": "feature_grid",
                "proof": "review_quote",
                "cta": "contact_prompt",
            },
        ),
        "feature_scroll": _structure_recipe(
            "product",
            hero_variant="feature-led",
            section_order=["hero", "features", "pricing", "proof", "cta"],
            keywords=("features", "demo", "workflow", "product"),
            density_bias="balanced",
            motion_bias="moderate",
            page_shell="feature_shell",
            navigation_modes=("brand_left_masthead", "centered_editorial_bar", "framed_sidebar_nav"),
            default_navigation_mode="brand_left_masthead",
            promoted_sections={
                "pricing": ["pricing"],
                "features": ["features", "metrics"],
                "proof": ["proof"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "feature_intro",
                "features": "feature_scroll",
                "pricing": "offer_cards",
                "proof": "proof_quote",
                "cta": "contact_prompt",
            },
        ),
        "contrast_split": _structure_recipe(
            "product",
            hero_variant="contrast",
            section_order=["hero", "proof", "features", "pricing", "cta"],
            keywords=("contrast", "split", "premium", "positioning"),
            density_bias="balanced",
            motion_bias="moderate",
            page_shell="contrast_shell",
            navigation_modes=("centered_editorial_bar", "split_utility_header", "brand_left_masthead"),
            default_navigation_mode="centered_editorial_bar",
            promoted_sections={
                "pricing": ["pricing"],
                "features": ["features", "metrics"],
                "proof": ["proof"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "contrast_intro",
                "proof": "lead_proof",
                "features": "support_features",
                "pricing": "pricing_cards",
                "cta": "contact_prompt",
            },
        ),
        "launch_countdown": _structure_recipe(
            "product",
            hero_variant="countdown",
            section_order=["hero", "metrics", "pricing", "features", "cta"],
            keywords=("launch", "countdown", "beta", "release"),
            density_bias="airy",
            motion_bias="energetic",
            page_shell="launch_shell",
            navigation_modes=("framed_sidebar_nav", "centered_editorial_bar", "split_utility_header"),
            default_navigation_mode="framed_sidebar_nav",
            promoted_sections={
                "pricing": ["pricing"],
                "features": ["features", "metrics"],
                "proof": ["proof"],
                "contact": ["cta"],
            },
            section_treatment_keys={
                "hero": "launch_intro",
                "metrics": "countdown_metrics",
                "pricing": "launch_offer",
                "features": "release_features",
                "cta": "contact_prompt",
            },
        ),
    },
}


def _slot_schema(
    *,
    text_slots: tuple[str, ...],
    list_slots: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "text_slots": list(text_slots),
        "list_slots": list_slots,
    }


SECTION_SCHEMAS: dict[str, dict[str, Any]] = {
    "store": _slot_schema(
        text_slots=(
            "hero_eyebrow",
            "hero_title",
            "hero_subtitle",
            "cta_text",
            "cta_note",
            "collections_title",
            "collections_intro",
            "products_title",
            "products_intro",
            "proof_quote",
            "proof_author",
        ),
        list_slots={
            "collections": {"item_fields": ["title", "desc", "meta"], "min_items": 2, "max_items": 4},
            "products": {"item_fields": ["title", "desc", "meta"], "min_items": 6, "max_items": 8},
        },
    ),
    "saas": _slot_schema(
        text_slots=(
            "hero_eyebrow",
            "hero_title",
            "hero_subtitle",
            "cta_text",
            "cta_note",
            "workflows_title",
            "workflows_intro",
            "features_title",
            "features_intro",
            "pricing_title",
            "pricing_intro",
            "proof_quote",
            "proof_author",
        ),
        list_slots={
            "workflows": {"item_fields": ["title", "desc", "meta"], "min_items": 3, "max_items": 4},
            "features": {"item_fields": ["title", "desc"], "min_items": 3, "max_items": 6},
            "offers": {"item_fields": ["title", "desc", "meta"], "min_items": 3, "max_items": 4},
        },
    ),
    "landing": _slot_schema(
        text_slots=(
            "hero_eyebrow",
            "hero_title",
            "hero_subtitle",
            "cta_text",
            "cta_note",
            "metrics_title",
            "metrics_intro",
            "features_title",
            "features_intro",
            "stat_1_value",
            "stat_1_label",
            "stat_2_value",
            "stat_2_label",
            "stat_3_value",
            "stat_3_label",
            "proof_quote",
            "proof_author",
        ),
        list_slots={
            "features": {"item_fields": ["title", "desc"], "min_items": 3, "max_items": 6},
            "offers": {"item_fields": ["title", "desc", "meta"], "min_items": 2, "max_items": 4},
        },
    ),
    "portfolio": _slot_schema(
        text_slots=(
            "hero_eyebrow",
            "hero_title",
            "hero_subtitle",
            "cta_text",
            "cta_note",
            "projects_title",
            "projects_intro",
            "about_title",
            "about_intro",
            "about_text",
            "capabilities_title",
            "capabilities_intro",
            "proof_quote",
            "proof_author",
        ),
        list_slots={
            "projects": {"item_fields": ["title", "desc", "meta"], "min_items": 4, "max_items": 6},
            "capabilities": {"item_fields": ["title", "desc"], "min_items": 3, "max_items": 5},
        },
    ),
    "business": _slot_schema(
        text_slots=(
            "hero_eyebrow",
            "hero_title",
            "hero_subtitle",
            "cta_text",
            "cta_note",
            "services_title",
            "services_intro",
            "process_title",
            "process_intro",
            "proof_quote",
            "proof_author",
        ),
        list_slots={
            "services": {"item_fields": ["title", "desc", "meta"], "min_items": 3, "max_items": 4},
            "process_steps": {"item_fields": ["title", "desc"], "min_items": 3, "max_items": 4},
        },
    ),
    "product": _slot_schema(
        text_slots=(
            "hero_eyebrow",
            "hero_title",
            "hero_subtitle",
            "price_badge",
            "cta_text",
            "cta_note",
            "metrics_title",
            "metrics_intro",
            "features_title",
            "features_intro",
            "pricing_title",
            "pricing_intro",
            "stat_1_value",
            "stat_1_label",
            "stat_2_value",
            "stat_2_label",
            "stat_3_value",
            "stat_3_label",
            "proof_quote",
            "proof_author",
        ),
        list_slots={
            "features": {"item_fields": ["title", "desc"], "min_items": 3, "max_items": 6},
            "offers": {"item_fields": ["title", "desc", "meta"], "min_items": 3, "max_items": 4},
        },
    ),
}


@dataclass(frozen=True)
class BriefInput:
    goal: str
    audience: str
    brand_tone: str
    content_density: str
    motion_level: str
    name: str
    notes: str
    prompt: str
    brand_assets: list[dict[str, str]] = field(default_factory=list)
    icon_style: str = ""

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    def to_prompt_text(self) -> str:
        pieces = [
            self.goal,
            self.audience,
            self.brand_tone,
            self.name,
            self.notes,
            self.icon_style,
            self.prompt,
        ]
        return ". ".join(item.strip() for item in pieces if item and item.strip())


@dataclass(frozen=True)
class PagePlan:
    slug: str
    label: str
    page_role: str
    template_file: str
    section_order: list[str]
    section_visibility: dict[str, bool]
    section_labels: dict[str, str]
    hero_variant: str
    is_home: bool = False

    def __post_init__(self) -> None:
        section_order = [str(item).strip() for item in self.section_order if str(item).strip()]
        section_visibility = {section: bool(self.section_visibility.get(section, True)) for section in section_order}
        section_labels = {
            section: str(self.section_labels.get(section, SECTION_LABELS.get(section, section.replace("_", " ").title()))).strip()
            or SECTION_LABELS.get(section, section.replace("_", " ").title())
            for section in section_order
        }
        object.__setattr__(self, "slug", _coerce_str(self.slug, "home"))
        object.__setattr__(self, "label", _coerce_str(self.label, "Home"))
        object.__setattr__(self, "page_role", _coerce_str(self.page_role, "overview"))
        object.__setattr__(self, "template_file", _coerce_str(self.template_file, "generated/site_builder.html"))
        object.__setattr__(self, "section_order", section_order)
        object.__setattr__(self, "section_visibility", section_visibility)
        object.__setattr__(self, "section_labels", section_labels)
        object.__setattr__(self, "hero_variant", _coerce_str(self.hero_variant, "statement"))
        object.__setattr__(self, "is_home", bool(self.is_home))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RenderPlan:
    template_key: str
    template_file: str
    theme_key: str
    art_direction: str
    layout_mode: str
    density: str
    motion_level: str
    section_order: list[str]
    section_visibility: dict[str, bool]
    hero_variant: str
    industry: str
    vibe: str
    keywords: list[str]
    confidence: float
    reasons: list[str]
    slot_schema: dict[str, Any]
    navigation_mode: str = ""
    page_shell: str = ""
    primary_page_slug: str = "home"
    pages: list[PagePlan] = field(default_factory=list)

    def __post_init__(self) -> None:
        recipe = _recipe_for(self.template_key, self.layout_mode)
        section_order = [str(item).strip() for item in self.section_order if str(item).strip()]
        section_visibility = {section: bool(self.section_visibility.get(section, True)) for section in section_order}
        pages = _coerce_page_plans(
            self.pages,
            template_key=self.template_key,
            template_file=self.template_file,
            layout_mode=self.layout_mode,
            hero_variant=self.hero_variant,
            section_order=section_order,
            section_visibility=section_visibility,
        )
        if not pages:
            pages = _default_pages_for_plan(
                template_key=self.template_key,
                template_file=self.template_file,
                layout_mode=self.layout_mode,
                hero_variant=self.hero_variant,
                section_order=section_order,
                section_visibility=section_visibility,
            )
        primary_page_slug = _coerce_str(self.primary_page_slug, "home")
        if primary_page_slug not in {page.slug for page in pages}:
            primary_page_slug = next((page.slug for page in pages if page.is_home), pages[0].slug if pages else "home")
        primary_page = next((page for page in pages if page.slug == primary_page_slug), pages[0] if pages else None)
        if primary_page is not None:
            section_order = list(primary_page.section_order)
            section_visibility = dict(primary_page.section_visibility)
        object.__setattr__(self, "section_order", section_order)
        object.__setattr__(self, "section_visibility", section_visibility)
        object.__setattr__(self, "hero_variant", _coerce_str(self.hero_variant, _coerce_str(recipe.get("hero_variant"), "statement")))
        object.__setattr__(
            self,
            "navigation_mode",
            _coerce_str(self.navigation_mode, _coerce_str(recipe.get("default_navigation_mode"), NAVIGATION_PATTERNS[0])),
        )
        object.__setattr__(self, "page_shell", _coerce_str(self.page_shell, _coerce_str(recipe.get("page_shell"), "campaign_shell")))
        object.__setattr__(self, "primary_page_slug", primary_page_slug)
        object.__setattr__(self, "pages", pages)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def page(self, slug: str | None = None) -> PagePlan:
        target_slug = _coerce_str(slug, self.primary_page_slug)
        return next((page for page in self.pages if page.slug == target_slug), self.pages[0])


def clean_json_response(raw_text: str) -> str:
    cleaned = raw_text.replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start != -1 and end != -1:
        return cleaned[start:end]
    return cleaned


def _coerce_str(value: Any, default: str = "") -> str:
    if isinstance(value, str):
        text = value.strip()
        return text if text else default
    return default


def _section_label_map(section_order: list[str]) -> dict[str, str]:
    return {
        section: SECTION_LABELS.get(section, section.replace("_", " ").title())
        for section in section_order
    }


def _page_sections_for_slug(template_key: str, slug: str, recipe: dict[str, Any]) -> list[str]:
    if slug == "home":
        return [str(item) for item in recipe.get("section_order", []) if str(item).strip()]
    promoted = recipe.get("promoted_sections", {})
    if isinstance(promoted, dict) and isinstance(promoted.get(slug), list):
        return [str(item).strip() for item in promoted.get(slug, []) if str(item).strip()]

    fallback_map: dict[str, list[str]] = {
        "collections": ["collections"],
        "products": ["products"],
        "reviews": ["proof"],
        "contact": ["cta"],
        "workflows": ["workflows"],
        "features": ["features", "metrics"],
        "pricing": ["pricing"],
        "services": ["services"],
        "process": ["process"],
        "projects": ["projects"],
        "about": ["about"],
        "capabilities": ["capabilities"],
        "proof": ["proof"],
    }
    return [item for item in fallback_map.get(slug, []) if item]


def _default_pages_for_plan(
    *,
    template_key: str,
    template_file: str,
    layout_mode: str,
    hero_variant: str,
    section_order: list[str],
    section_visibility: dict[str, bool],
) -> list[PagePlan]:
    recipe = _recipe_for(template_key, layout_mode)
    pages: list[PagePlan] = [
        PagePlan(
            slug="home",
            label="Home",
            page_role="overview",
            template_file=template_file,
            section_order=section_order or [str(item) for item in recipe.get("section_order", []) if str(item).strip()],
            section_visibility=section_visibility or _section_visibility(section_order or list(recipe.get("section_order", []))),
            section_labels=_section_label_map(section_order or list(recipe.get("section_order", []))),
            hero_variant=hero_variant or _coerce_str(recipe.get("hero_variant"), "statement"),
            is_home=True,
        )
    ]

    for entry in TEMPLATE_PAGE_BLUEPRINTS.get(template_key, []):
        slug = _coerce_str(entry.get("slug"))
        page_sections = _page_sections_for_slug(template_key, slug, recipe)
        if not page_sections:
            continue
        visibility = {section: bool(section_visibility.get(section, True)) for section in page_sections}
        pages.append(
            PagePlan(
                slug=slug,
                label=_coerce_str(entry.get("label"), slug.replace("_", " ").title()),
                page_role=_coerce_str(entry.get("page_role"), slug),
                template_file=template_file,
                section_order=page_sections,
                section_visibility=visibility,
                section_labels=_section_label_map(page_sections),
                hero_variant=hero_variant or _coerce_str(recipe.get("hero_variant"), "statement"),
                is_home=False,
            )
        )
    return pages


def _coerce_page_plans(
    value: Any,
    *,
    template_key: str,
    template_file: str,
    layout_mode: str,
    hero_variant: str,
    section_order: list[str],
    section_visibility: dict[str, bool],
) -> list[PagePlan]:
    if not isinstance(value, list) or not value:
        return []

    pages: list[PagePlan] = []
    for raw_page in value:
        if isinstance(raw_page, PagePlan):
            pages.append(raw_page)
            continue
        if not isinstance(raw_page, dict):
            continue
        slug = _coerce_str(raw_page.get("slug"))
        page_sections = [
            str(item).strip()
            for item in raw_page.get("section_order", [])
            if str(item).strip()
        ]
        if slug == "home" and not page_sections:
            page_sections = list(section_order)
        visibility = {
            section: bool((raw_page.get("section_visibility") or {}).get(section, section_visibility.get(section, True)))
            for section in page_sections
        }
        pages.append(
            PagePlan(
                slug=slug or "home",
                label=_coerce_str(raw_page.get("label"), slug.replace("_", " ").title() if slug else "Home"),
                page_role=_coerce_str(raw_page.get("page_role"), slug or "overview"),
                template_file=_coerce_str(raw_page.get("template_file"), template_file),
                section_order=page_sections,
                section_visibility=visibility,
                section_labels=raw_page.get("section_labels") if isinstance(raw_page.get("section_labels"), dict) else _section_label_map(page_sections),
                hero_variant=_coerce_str(raw_page.get("hero_variant"), hero_variant),
                is_home=bool(raw_page.get("is_home", slug == "home")),
            )
        )
    return pages


def _coerce_list_of_str(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    output: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        normalized = item.strip().lower()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        output.append(normalized)
    return output


def _coerce_brand_assets(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []

    assets: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for index, item in enumerate(value):
        if len(assets) >= MAX_BRAND_ASSETS or not isinstance(item, dict):
            continue

        data_url = _coerce_str(item.get("data_url"))
        if not data_url.startswith("data:image/") or len(data_url) > MAX_BRAND_ASSET_DATA_URL_LENGTH:
            continue

        header = data_url.split(",", 1)[0].lower()
        mime_type = _coerce_str(item.get("mime_type")).lower()
        if not mime_type and header.startswith("data:"):
            mime_type = header[5:].split(";", 1)[0].strip().lower()
        if mime_type not in ALLOWED_BRAND_ASSET_MIME_TYPES:
            continue

        if data_url in seen_urls:
            continue
        seen_urls.add(data_url)

        name = _coerce_str(item.get("name"), f"Brand asset {index + 1}")[:MAX_BRAND_ASSET_NAME_LENGTH]
        alt = _coerce_str(item.get("alt"), name or f"Brand asset {index + 1}")[:MAX_BRAND_ASSET_ALT_LENGTH]
        asset_id = _coerce_str(item.get("id"), f"brand-asset-{index + 1}")[:40]

        assets.append(
            {
                "id": asset_id or f"brand-asset-{index + 1}",
                "name": name or f"Brand asset {index + 1}",
                "alt": alt or name or f"Brand asset {index + 1}",
                "mime_type": mime_type,
                "data_url": data_url,
            }
        )
    return assets


def _normalize_prompt(prompt: str) -> str:
    return re.sub(r"\s+", " ", prompt.lower()).strip()


def _tokenize(prompt: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9\-]*", prompt.lower())


def _stem_token(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("s") and len(token) > 3 and not token.endswith("ss"):
        return token[:-1]
    return token


def _build_token_set(tokens: list[str]) -> set[str]:
    token_set: set[str] = set()
    for token in tokens:
        token_set.add(token)
        token_set.add(_stem_token(token))
    return token_set


def _signal_match(signal: str, *, prompt: str, token_set: set[str]) -> bool:
    normalized = signal.lower().strip()
    if not normalized:
        return False
    if " " in normalized:
        return normalized in prompt
    if "-" in normalized and normalized.replace("-", " ") in prompt:
        return True
    return normalized in token_set


def _score_signal_groups(
    prompt: str,
    token_set: set[str],
    signal_map: dict[str, dict[str, tuple[str, ...]]],
    *,
    phrase_weight: float,
    strong_weight: float,
    support_weight: float,
) -> tuple[dict[str, float], dict[str, int]]:
    scores: dict[str, float] = {}
    hits: dict[str, int] = {}

    for key, rules in signal_map.items():
        score = 0.0
        hit_count = 0
        for phrase in rules.get("phrases", ()):
            if _signal_match(phrase, prompt=prompt, token_set=token_set):
                score += phrase_weight
                hit_count += 1
        for term in rules.get("strong_terms", ()):
            if _signal_match(term, prompt=prompt, token_set=token_set):
                score += strong_weight
                hit_count += 1
        for term in rules.get("support_terms", ()):
            if _signal_match(term, prompt=prompt, token_set=token_set):
                score += support_weight
                hit_count += 1
        scores[key] = round(score, 4)
        hits[key] = hit_count

    return scores, hits


def _score_by_keywords(prompt: str, token_set: set[str], keyword_map: dict[str, tuple[str, ...]]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for key, words in keyword_map.items():
        score = 0.0
        for word in words:
            if _signal_match(word, prompt=prompt, token_set=token_set):
                score += 1.0
        scores[key] = score
    return scores


def _top_two(scores: dict[str, float]) -> tuple[tuple[str, float], tuple[str, float]]:
    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    if not ordered:
        return ("landing", 0.0), ("landing", 0.0)
    if len(ordered) == 1:
        return ordered[0], ordered[0]
    return ordered[0], ordered[1]


def _extract_keywords(prompt: str) -> list[str]:
    terms = re.findall(r"[a-z0-9][a-z0-9\-]+", prompt.lower())
    output: list[str] = []
    seen: set[str] = set()
    for term in terms:
        if term in STOPWORDS or len(term) < 3 or term in seen:
            continue
        output.append(term)
        seen.add(term)
        if len(output) >= 8:
            break
    return output


def _safe_default_key(allowed_keys: set[str], preferred: str) -> str:
    if preferred in allowed_keys:
        return preferred
    if not allowed_keys:
        return preferred
    return sorted(allowed_keys)[0]


def _resolve_choice(value: Any, *, allowed: set[str], default: str) -> str:
    chosen = _coerce_str(value, default).lower()
    if chosen not in allowed:
        return default
    return chosen


def _infer_category(prompt: str, token_set: set[str], keyword_map: dict[str, tuple[str, ...]], default: str) -> str:
    scores = _score_by_keywords(prompt, token_set, keyword_map)
    winner, score = _top_two(scores)[0]
    return winner if score > 0 else default


def _compute_rule_confidence(top_score: float, gap: float, signal_hits: int) -> float:
    if top_score <= 0:
        return 0.24
    confidence = 0.34 + min(top_score, 10.0) * 0.055 + min(gap, 3.0) * 0.12 + min(signal_hits, 7) * 0.03
    return max(0.0, min(0.97, confidence))


def _normalize_density(value: str) -> str:
    return value if value in {"airy", "balanced", "dense"} else "balanced"


def _normalize_motion(value: str) -> str:
    return value if value in {"calm", "moderate", "energetic"} else "moderate"


def normalize_brief(raw_prompt: str = "", raw_brief: dict[str, Any] | None = None) -> BriefInput:
    raw_brief = raw_brief or {}
    goal = _coerce_str(raw_brief.get("goal"), raw_prompt)
    audience = _coerce_str(raw_brief.get("audience"), "General audience")
    brand_tone = _coerce_str(raw_brief.get("brand_tone"), "Clear and modern")
    content_density = _normalize_density(_coerce_str(raw_brief.get("content_density"), "balanced").lower())
    motion_level = _normalize_motion(_coerce_str(raw_brief.get("motion_level"), "moderate").lower())
    name = _coerce_str(raw_brief.get("name"))
    notes = _coerce_str(raw_brief.get("notes"), raw_prompt if raw_prompt and raw_prompt != goal else "")
    prompt = _coerce_str(raw_prompt)
    brand_assets = _coerce_brand_assets(raw_brief.get("brand_assets"))
    icon_style = _coerce_str(raw_brief.get("icon_style"))[:220]
    return BriefInput(
        goal=goal,
        audience=audience,
        brand_tone=brand_tone,
        content_density=content_density,
        motion_level=motion_level,
        name=name,
        notes=notes,
        prompt=prompt,
        brand_assets=brand_assets,
        icon_style=icon_style,
    )


def _apply_intent_boosts(
    *,
    token_set: set[str],
    template_scores: dict[str, float],
    template_hits: dict[str, int],
    art_scores: dict[str, float],
    art_hits: dict[str, int],
) -> list[str]:
    reasons: list[str] = []

    personal_words = {"my", "me", "personal", "i"}
    creator_words = {"developer", "designer", "photographer", "artist", "freelancer", "portfolio"}
    if personal_words.intersection(token_set) and creator_words.intersection(token_set):
        template_scores["portfolio"] = template_scores.get("portfolio", 0.0) + 1.9
        template_hits["portfolio"] = template_hits.get("portfolio", 0) + 1
        reasons.append("Intent boost favored portfolio.")

    store_words = {"store", "shop", "ecommerce", "catalog", "collection", "checkout", "buy", "product", "products"}
    if store_words.intersection(token_set):
        template_scores["store"] = template_scores.get("store", 0.0) + 2.1
        template_hits["store"] = template_hits.get("store", 0) + 1
        reasons.append("Intent boost favored store.")

    saas_words = {"saas", "software", "copilot", "app", "dashboard", "workflow", "automation", "trial", "demo"}
    launch_words = {"launch", "preorder", "beta", "release", "roadmap"}
    if saas_words.intersection(token_set):
        template_scores["saas"] = template_scores.get("saas", 0.0) + 2.0
        template_hits["saas"] = template_hits.get("saas", 0) + 1
        reasons.append("Intent boost favored saas.")
    if launch_words.intersection(token_set):
        template_scores["saas"] = template_scores.get("saas", 0.0) + 0.8
        template_hits["saas"] = template_hits.get("saas", 0) + 1

    business_words = {"service", "services", "agency", "consulting", "book", "appointment", "company", "business"}
    if business_words.intersection(token_set):
        template_scores["business"] = template_scores.get("business", 0.0) + 1.6
        template_hits["business"] = template_hits.get("business", 0) + 1
        reasons.append("Intent boost favored business.")

    kids_words = {"kids", "kid", "children", "child", "school", "classroom", "workshop"}
    if kids_words.intersection(token_set):
        art_scores["playful_blocks"] = art_scores.get("playful_blocks", 0.0) + 2.2
        art_hits["playful_blocks"] = art_hits.get("playful_blocks", 0) + 1
        reasons.append("Youth audience boosted playful art direction.")

    premium_words = {"luxury", "premium", "exclusive", "high-end", "upscale", "elegant", "refined"}
    if premium_words.intersection(token_set):
        art_scores["luxury_serif"] = art_scores.get("luxury_serif", 0.0) + 2.0
        art_hits["luxury_serif"] = art_hits.get("luxury_serif", 0) + 1
        reasons.append("Premium language boosted luxury art direction.")

    cyber_words = {"cyber", "neon", "futuristic", "hacker", "matrix", "gaming", "dark"}
    if cyber_words.intersection(token_set):
        art_scores["cyber_signal"] = art_scores.get("cyber_signal", 0.0) + 2.1
        art_hits["cyber_signal"] = art_hits.get("cyber_signal", 0) + 1
        reasons.append("Futuristic language boosted cyber art direction.")

    warm_words = {"approachable", "friendly", "warm", "welcoming", "human"}
    if warm_words.intersection(token_set):
        art_scores["warm_gradient"] = art_scores.get("warm_gradient", 0.0) + 1.7
        art_hits["warm_gradient"] = art_hits.get("warm_gradient", 0) + 1

    coastal_words = {"coastal", "ocean", "sea", "breeze", "shore", "resort"}
    if coastal_words.intersection(token_set):
        art_scores["coastal_breeze"] = art_scores.get("coastal_breeze", 0.0) + 1.9
        art_hits["coastal_breeze"] = art_hits.get("coastal_breeze", 0) + 1

    monochrome_words = {"monochrome", "swiss", "grid", "minimalist", "black", "white"}
    if monochrome_words.intersection(token_set):
        art_scores["mono_signal"] = art_scores.get("mono_signal", 0.0) + 1.8
        art_hits["mono_signal"] = art_hits.get("mono_signal", 0) + 1

    botanical_words = {"botanical", "organic", "forest", "earthy", "natural", "garden"}
    if botanical_words.intersection(token_set):
        art_scores["botanical_noir"] = art_scores.get("botanical_noir", 0.0) + 1.8
        art_hits["botanical_noir"] = art_hits.get("botanical_noir", 0) + 1

    pop_words = {"expressive", "electric", "cobalt", "vivid", "studio", "magazine"}
    if pop_words.intersection(token_set):
        art_scores["studio_pop"] = art_scores.get("studio_pop", 0.0) + 1.8
        art_hits["studio_pop"] = art_hits.get("studio_pop", 0) + 1

    graphic_words = {"poster", "graphic", "raw", "brutalist", "contrast"}
    if graphic_words.intersection(token_set):
        art_scores["brutalist_poster"] = art_scores.get("brutalist_poster", 0.0) + 1.8
        art_hits["brutalist_poster"] = art_hits.get("brutalist_poster", 0) + 1

    return reasons[:4]


def _rank_layouts(
    template_key: str,
    *,
    prompt: str,
    token_set: set[str],
    density: str,
    motion_level: str,
    vibe: str,
) -> list[str]:
    recipes = LAYOUT_LIBRARY.get(template_key, {})
    scores: list[tuple[str, float]] = []
    for layout_mode, recipe in recipes.items():
        score = 0.0
        for hint in recipe.get("keywords", ()):
            if _signal_match(hint, prompt=prompt, token_set=token_set):
                score += 1.1
        if recipe.get("density_bias") == density:
            score += 0.8
        if recipe.get("motion_bias") == motion_level:
            score += 0.8
        if vibe in recipe.get("keywords", ()):
            score += 0.6
        scores.append((layout_mode, score))

    scores.sort(key=lambda item: item[1], reverse=True)
    ordered = [item[0] for item in scores]
    if ordered:
        return ordered
    return list(recipes.keys())


def _unique_keys(values: list[str], *, allowed: set[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in allowed or value in seen:
            continue
        ordered.append(value)
        seen.add(value)
    return ordered


def _contextual_art_ranking(
    *,
    template_key: str,
    industry: str,
    vibe: str,
    density: str,
    motion_level: str,
    allowed_art_keys: set[str],
) -> list[str]:
    ranking: list[str] = []
    industry_biases = ART_DIRECTION_INDUSTRY_BIASES.get(industry, ())
    template_biases = TEMPLATE_ART_DIRECTION_BIASES.get(template_key, ())

    if industry_biases and industry not in {"general", "technology"}:
        ranking.extend(industry_biases)
        ranking.extend(template_biases)
    else:
        ranking.extend(template_biases)
        ranking.extend(industry_biases)
    ranking.extend(ART_DIRECTION_VIBE_BIASES.get(vibe, ()))

    if motion_level == "energetic":
        ranking.extend(("cyber_signal", "studio_pop", "brutalist_poster"))
    elif motion_level == "calm":
        ranking.extend(("luxury_serif", "coastal_breeze", "warm_gradient"))

    if density == "airy":
        ranking.extend(("coastal_breeze", "modern_editorial", "warm_gradient"))
    elif density == "dense":
        ranking.extend(("mono_signal", "brutalist_poster", "cyber_signal"))

    ranking.extend(sorted(allowed_art_keys))
    return _unique_keys(ranking, allowed=allowed_art_keys)


def _art_direction_distance(primary: str, candidate: str) -> float:
    if primary == candidate:
        return 0.0

    primary_traits = ART_DIRECTION_TRAITS.get(primary, {})
    candidate_traits = ART_DIRECTION_TRAITS.get(candidate, {})
    score = 0.0

    if primary_traits.get("family") != candidate_traits.get("family"):
        score += 2.2
    if primary_traits.get("temperature") != candidate_traits.get("temperature"):
        score += 1.0
    if primary_traits.get("contrast") != candidate_traits.get("contrast"):
        score += 1.0
    if primary_traits.get("energy") != candidate_traits.get("energy"):
        score += 0.8

    return score


def _layout_distance(template_key: str, primary: str, candidate: str) -> float:
    if primary == candidate:
        return 0.0

    primary_recipe = _recipe_for(template_key, primary)
    candidate_recipe = _recipe_for(template_key, candidate)
    score = 0.0

    if primary_recipe.get("hero_variant") != candidate_recipe.get("hero_variant"):
        score += 2.0
    if primary_recipe.get("density_bias") != candidate_recipe.get("density_bias"):
        score += 0.8
    if primary_recipe.get("motion_bias") != candidate_recipe.get("motion_bias"):
        score += 0.8

    primary_sections = list(primary_recipe.get("section_order", ()))
    candidate_sections = list(candidate_recipe.get("section_order", ()))
    shared = set(primary_sections).intersection(candidate_sections)
    order_changes = sum(
        1
        for section in shared
        if primary_sections.index(section) != candidate_sections.index(section)
    )
    score += min(float(order_changes), 3.0) * 0.5
    return score


def _pick_diverse_options(
    ordered_keys: list[str],
    *,
    primary: str,
    distance_fn: Any,
    score_lookup: dict[str, float] | None = None,
    limit: int = 3,
) -> list[str]:
    selected: list[str] = []
    if primary in ordered_keys:
        selected.append(primary)
    elif ordered_keys:
        selected.append(ordered_keys[0])

    remaining = [key for key in ordered_keys if key not in selected]
    while remaining and len(selected) < limit:
        best_key = remaining[0]
        best_score = float("-inf")
        for key in remaining:
            diversity = min(distance_fn(existing, key) for existing in selected)
            routing_score = (score_lookup or {}).get(key, 0.0)
            combined = diversity * 3.4 + routing_score
            if combined > best_score:
                best_key = key
                best_score = combined
        selected.append(best_key)
        remaining = [key for key in remaining if key != best_key]

    return selected


def _apply_contextual_art_biases(
    art_scores: dict[str, float],
    art_hits: dict[str, int],
    *,
    contextual_ranking: list[str],
    template_key: str,
    industry: str,
    vibe: str,
) -> list[str]:
    weights = (1.1, 0.7, 0.4)
    for index, art_direction in enumerate(contextual_ranking[: len(weights)]):
        art_scores[art_direction] = art_scores.get(art_direction, 0.0) + weights[index]
        art_hits[art_direction] = art_hits.get(art_direction, 0) + 1

    if not contextual_ranking:
        return []
    return [
        f"Context routing favored '{contextual_ranking[0]}' for {template_key}/{industry}/{vibe}."
    ]


def _section_visibility(section_order: list[str], overrides: dict[str, bool] | None = None) -> dict[str, bool]:
    visibility = {section: True for section in section_order}
    for key, value in (overrides or {}).items():
        if key in visibility:
            visibility[key] = bool(value)
    return visibility


def _template_file_for(template_key: str, template_catalog: dict[str, dict[str, Any]]) -> str:
    template_config = template_catalog.get(template_key, {})
    return _coerce_str(template_config.get("template_file"), "generated/site_builder.html")


def _recipe_for(template_key: str, layout_mode: str) -> dict[str, Any]:
    recipes = LAYOUT_LIBRARY.get(template_key, {})
    if layout_mode in recipes:
        return recipes[layout_mode]
    if recipes:
        return recipes[sorted(recipes.keys())[0]]
    return {
        "hero_variant": "statement",
        "section_order": ["hero", "cta"],
        "keywords": (),
        "page_shell": "campaign_shell",
        "navigation_modes": list(NAVIGATION_PATTERNS[:3]),
        "default_navigation_mode": NAVIGATION_PATTERNS[0],
        "default_page_map": ["contact"],
        "promoted_sections": {"contact": ["cta"]},
        "section_treatment_keys": {},
    }


def _make_plan(
    *,
    template_key: str,
    art_direction: str,
    layout_mode: str,
    density: str,
    motion_level: str,
    industry: str,
    vibe: str,
    keywords: list[str],
    confidence: float,
    reasons: list[str],
    template_catalog: dict[str, dict[str, Any]],
    section_visibility: dict[str, bool] | None = None,
    navigation_mode: str | None = None,
) -> RenderPlan:
    recipe = _recipe_for(template_key, layout_mode)
    section_order = list(recipe.get("section_order", ["hero", "cta"]))
    slot_schema = SECTION_SCHEMAS.get(template_key, {"text_slots": [], "list_slots": {}})
    return RenderPlan(
        template_key=template_key,
        template_file=_template_file_for(template_key, template_catalog),
        theme_key=art_direction,
        art_direction=art_direction,
        layout_mode=layout_mode,
        density=density,
        motion_level=motion_level,
        section_order=section_order,
        section_visibility=_section_visibility(section_order, section_visibility),
        hero_variant=_coerce_str(recipe.get("hero_variant"), "statement"),
        industry=industry,
        vibe=vibe,
        keywords=keywords[:8],
        confidence=round(confidence, 3),
        reasons=reasons[:5],
        slot_schema=slot_schema,
        navigation_mode=_coerce_str(navigation_mode, _coerce_str(recipe.get("default_navigation_mode"), NAVIGATION_PATTERNS[0])),
        page_shell=_coerce_str(recipe.get("page_shell"), "campaign_shell"),
        primary_page_slug="home",
        pages=[],
    )


def _llm_override_profile(
    model: Any,
    *,
    brief: BriefInput,
    template_keys: list[str],
    art_keys: list[str],
    layout_keys: list[str],
) -> dict[str, Any] | None:
    prompt = f"""
You are a website taste-routing assistant.
Return VALID JSON ONLY.

Choose exactly one template_key from {template_keys}.
Choose exactly one art_direction from {art_keys}.
Choose exactly one layout_mode from {layout_keys}.
Choose exactly one density from ["airy", "balanced", "dense"].
Choose exactly one motion_level from ["calm", "moderate", "energetic"].

JSON schema:
{{
  "template_key": "landing",
  "art_direction": "modern_editorial",
  "layout_mode": "split_hero",
  "density": "balanced",
  "motion_level": "moderate",
  "industry": "technology",
  "vibe": "bold",
  "keywords": ["launch", "startup", "demo"],
  "confidence": 0.78,
  "reason": "Clear launch framing with premium positioning"
}}

BRIEF:
{brief.to_prompt_text()}
""".strip()
    response = model.generate_content(prompt)
    raw = clean_json_response(getattr(response, "text", ""))
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        return None
    return {
        "template_key": _coerce_str(parsed.get("template_key")).lower(),
        "art_direction": _coerce_str(parsed.get("art_direction")).lower(),
        "layout_mode": _coerce_str(parsed.get("layout_mode")).lower(),
        "density": _normalize_density(_coerce_str(parsed.get("density")).lower()),
        "motion_level": _normalize_motion(_coerce_str(parsed.get("motion_level")).lower()),
        "industry": _coerce_str(parsed.get("industry"), "general"),
        "vibe": _coerce_str(parsed.get("vibe"), "clean"),
        "keywords": _coerce_list_of_str(parsed.get("keywords")),
        "confidence": max(0.0, min(1.0, float(parsed.get("confidence", 0.0)))),
        "reason": _coerce_str(parsed.get("reason"), "LLM routing"),
    }


def _density_sequence(base: str) -> list[str]:
    mapping = {
        "airy": ["airy", "dense", "balanced"],
        "balanced": ["balanced", "airy", "dense"],
        "dense": ["dense", "airy", "balanced"],
    }
    return mapping.get(base, ["balanced", "airy", "dense"])


def _motion_sequence(base: str) -> list[str]:
    mapping = {
        "calm": ["calm", "moderate", "energetic"],
        "moderate": ["moderate", "calm", "energetic"],
        "energetic": ["energetic", "moderate", "calm"],
    }
    return mapping.get(base, ["moderate", "calm", "energetic"])


def build_render_variants(
    user_prompt: str,
    *,
    brief: BriefInput | dict[str, Any] | None = None,
    model: Any | None = None,
    overrides: dict[str, Any] | None = None,
    theme_catalog: dict[str, Any] | None = None,
    template_catalog: dict[str, dict[str, Any]] | None = None,
) -> list[RenderPlan]:
    if theme_catalog is None:
        theme_catalog = {"modern_editorial": {}}
    if template_catalog is None:
        template_catalog = {"landing": {"template_file": "generated/site_builder.html", "slot_schema": {}}}

    brief_payload = brief.to_dict() if isinstance(brief, BriefInput) else (brief if isinstance(brief, dict) else {})
    brief_input = brief if isinstance(brief, BriefInput) else normalize_brief(user_prompt, brief)
    prompt = _normalize_prompt(brief_input.to_prompt_text())
    tokens = _tokenize(prompt)
    token_set = _build_token_set(tokens)
    has_density_preference = _coerce_str(brief_payload.get("content_density")).lower() in {"airy", "balanced", "dense"}
    has_motion_preference = _coerce_str(brief_payload.get("motion_level")).lower() in {"calm", "moderate", "energetic"}

    primary_template_keys = [key for key in PRIMARY_TEMPLATE_KEYS if key in template_catalog]
    template_keys = primary_template_keys or list(template_catalog.keys())
    art_keys = list(theme_catalog.keys())

    template_scores, template_hits = _score_signal_groups(
        prompt,
        token_set,
        DEFAULT_TEMPLATE_SIGNALS,
        phrase_weight=2.8,
        strong_weight=1.7,
        support_weight=0.9,
    )
    art_scores, art_hits = _score_signal_groups(
        prompt,
        token_set,
        ART_DIRECTION_SIGNALS,
        phrase_weight=2.4,
        strong_weight=1.6,
        support_weight=0.8,
    )
    density = brief_input.content_density or _infer_category(prompt, token_set, DENSITY_KEYWORDS, "balanced")
    motion_level = brief_input.motion_level or _infer_category(prompt, token_set, MOTION_KEYWORDS, "moderate")
    industry = _infer_category(prompt, token_set, INDUSTRY_KEYWORDS, "general")
    vibe = _infer_category(prompt, token_set, VIBE_KEYWORDS, "clean")
    keywords = _extract_keywords(prompt)
    reasons = _apply_intent_boosts(
        token_set=token_set,
        template_scores=template_scores,
        template_hits=template_hits,
        art_scores=art_scores,
        art_hits=art_hits,
    )

    ranked_template_scores = {key: template_scores.get(key, 0.0) for key in template_keys}
    for key in template_keys:
        template_hits.setdefault(key, 0)

    (best_template, top_template_score), (_, second_template_score) = _top_two(ranked_template_scores)
    contextual_art_ranking = _contextual_art_ranking(
        template_key=best_template,
        industry=industry,
        vibe=vibe,
        density=density,
        motion_level=motion_level,
        allowed_art_keys=set(art_keys),
    )
    reasons.extend(
        _apply_contextual_art_biases(
            art_scores,
            art_hits,
            contextual_ranking=contextual_art_ranking,
            template_key=best_template,
            industry=industry,
            vibe=vibe,
        )
    )
    ranked_art_scores = {key: art_scores.get(key, 0.0) for key in art_keys}
    (best_art, _), _ = _top_two(ranked_art_scores)
    template_gap = max(0.0, top_template_score - second_template_score)
    confidence = _compute_rule_confidence(top_template_score, template_gap, template_hits.get(best_template, 0))
    reasons = [f"Rule routing picked '{best_template}' with layout diversity enabled."] + reasons

    layout_ranking = _rank_layouts(
        best_template,
        prompt=prompt,
        token_set=token_set,
        density=density,
        motion_level=motion_level,
        vibe=vibe,
    )
    preferred_layouts = [key for key in PRIMARY_VARIANT_LAYOUTS.get(best_template, ()) if key in LAYOUT_LIBRARY.get(best_template, {})]
    if preferred_layouts:
        layout_ranking = [key for key in layout_ranking if key in preferred_layouts]
        for key in preferred_layouts:
            if key not in layout_ranking:
                layout_ranking.append(key)
    best_layout = layout_ranking[0] if layout_ranking else _safe_default_key(set(LAYOUT_LIBRARY.get(best_template, {})), "split_hero")

    should_use_llm = model is not None and (template_gap <= 0.75 or top_template_score < 2.6)
    if should_use_llm:
        try:
            llm_result = _llm_override_profile(
                model,
                brief=brief_input,
                template_keys=template_keys,
                art_keys=art_keys,
                layout_keys=preferred_layouts or list(LAYOUT_LIBRARY.get(best_template, {}).keys()) or [best_layout],
            )
            if llm_result:
                best_template = _resolve_choice(llm_result["template_key"], allowed=set(template_keys), default=best_template)
                best_art = _resolve_choice(llm_result["art_direction"], allowed=set(art_keys), default=best_art)
                layout_choices = set(LAYOUT_LIBRARY.get(best_template, {}).keys())
                best_layout = _resolve_choice(llm_result["layout_mode"], allowed=layout_choices, default=best_layout)
                density = llm_result["density"] or density
                motion_level = llm_result["motion_level"] or motion_level
                industry = llm_result["industry"] or industry
                vibe = llm_result["vibe"] or vibe
                if llm_result["keywords"]:
                    keywords = llm_result["keywords"]
                confidence = max(confidence, llm_result["confidence"])
                reasons.append(f"LLM routing used: {llm_result['reason']}.")
        except Exception:
            reasons.append("LLM routing failed; kept rule routing.")

    if not keywords:
        keywords = [industry, vibe, best_template, best_art]

    if confidence < 0.55:
        best_template = _safe_default_key(set(template_keys), "landing")
        fallback_ranking = _contextual_art_ranking(
            template_key=best_template,
            industry=industry,
            vibe=vibe,
            density=density,
            motion_level=motion_level,
            allowed_art_keys=set(art_keys),
        )
        best_art = fallback_ranking[0] if fallback_ranking else _safe_default_key(set(art_keys), "modern_editorial")
        if not has_density_preference:
            density = "balanced"
        if not has_motion_preference:
            motion_level = "moderate"
        confidence = 0.55
        reasons.append("Confidence low; applied safe fallback profile.")

    if overrides:
        template_override = overrides.get("template_key")
        art_override = overrides.get("art_direction") or overrides.get("theme_key")
        layout_override = overrides.get("layout_mode")
        density_override = overrides.get("density")
        motion_override = overrides.get("motion_level")

        best_template = _resolve_choice(template_override, allowed=set(template_keys), default=best_template)
        best_art = _resolve_choice(art_override, allowed=set(art_keys), default=best_art)
        layout_choices = set(LAYOUT_LIBRARY.get(best_template, {}).keys())
        best_layout = _resolve_choice(layout_override, allowed=layout_choices, default=best_layout)
        density = _normalize_density(_coerce_str(density_override, density).lower())
        motion_level = _normalize_motion(_coerce_str(motion_override, motion_level).lower())

    layout_ranking = _rank_layouts(
        best_template,
        prompt=prompt,
        token_set=token_set,
        density=density,
        motion_level=motion_level,
        vibe=vibe,
    )
    preferred_layouts = [key for key in PRIMARY_VARIANT_LAYOUTS.get(best_template, ()) if key in LAYOUT_LIBRARY.get(best_template, {})]
    if preferred_layouts:
        layout_ranking = [key for key in layout_ranking if key in preferred_layouts]
        for key in preferred_layouts:
            if key not in layout_ranking:
                layout_ranking.append(key)
    if best_layout in layout_ranking:
        layout_ranking.remove(best_layout)
    layout_ranking.insert(0, best_layout)

    scored_art_ranking = [
        key
        for key, _ in sorted(ranked_art_scores.items(), key=lambda item: item[1], reverse=True)
        if key in art_keys
    ]
    if not scored_art_ranking:
        scored_art_ranking = list(art_keys)
    art_ranking = _pick_diverse_options(
        scored_art_ranking,
        primary=best_art,
        distance_fn=_art_direction_distance,
        score_lookup=ranked_art_scores,
        limit=max(3, min(4, len(scored_art_ranking))),
    )
    layout_ranking = _pick_diverse_options(
        layout_ranking,
        primary=best_layout,
        distance_fn=lambda existing, candidate: _layout_distance(best_template, existing, candidate),
        limit=max(3, min(4, len(layout_ranking))),
    )

    variants: list[RenderPlan] = []
    used_pairs: set[tuple[str, str, str, str, str, str]] = set()
    section_override = overrides.get("section_visibility") if isinstance(overrides, dict) else None
    density_choices = _density_sequence(density)
    motion_choices = _motion_sequence(motion_level)
    navigation_override = overrides.get("navigation_mode") if isinstance(overrides, dict) else None
    chosen_navigation_modes: list[str] = []

    def navigation_choice(layout_mode: str, index: int) -> str:
        recipe = _recipe_for(best_template, layout_mode)
        allowed_navigation_modes = [
            str(item).strip()
            for item in recipe.get("navigation_modes", list(NAVIGATION_PATTERNS))
            if str(item).strip()
        ] or list(NAVIGATION_PATTERNS)
        default_navigation_mode = _coerce_str(
            recipe.get("default_navigation_mode"),
            allowed_navigation_modes[0],
        )
        if navigation_override:
            return _resolve_choice(
                navigation_override,
                allowed=set(allowed_navigation_modes),
                default=default_navigation_mode,
            )
        preferred = allowed_navigation_modes[index % len(allowed_navigation_modes)]
        if preferred not in chosen_navigation_modes:
            chosen_navigation_modes.append(preferred)
            return preferred
        for candidate in allowed_navigation_modes:
            if candidate not in chosen_navigation_modes:
                chosen_navigation_modes.append(candidate)
                return candidate
        chosen_navigation_modes.append(default_navigation_mode)
        return default_navigation_mode

    candidate_specs = [
        (
            layout_ranking[0] if layout_ranking else best_layout,
            art_ranking[0] if art_ranking else best_art,
            navigation_choice(layout_ranking[0] if layout_ranking else best_layout, 0),
            density_choices[0],
            motion_choices[0],
            confidence,
            list(reasons),
        ),
    ]
    candidate_specs.append(
        (
            layout_ranking[1] if len(layout_ranking) > 1 else best_layout,
            art_ranking[1] if len(art_ranking) > 1 else best_art,
            navigation_choice(layout_ranking[1] if len(layout_ranking) > 1 else best_layout, 1),
            density_choices[1] if len(density_choices) > 1 else density,
            motion_choices[1] if len(motion_choices) > 1 else motion_level,
            max(0.55, confidence - 0.05),
            ["Variant widens the visual system with a more distant art and layout pairing."],
        )
    )
    candidate_specs.append(
        (
            layout_ranking[2] if len(layout_ranking) > 2 else (layout_ranking[1] if len(layout_ranking) > 1 else best_layout),
            art_ranking[2] if len(art_ranking) > 2 else (art_ranking[1] if len(art_ranking) > 1 else best_art),
            navigation_choice(
                layout_ranking[2] if len(layout_ranking) > 2 else (layout_ranking[1] if len(layout_ranking) > 1 else best_layout),
                2,
            ),
            density_choices[2] if len(density_choices) > 2 else density,
            motion_choices[2] if len(motion_choices) > 2 else motion_level,
            max(0.55, confidence - 0.08),
            ["Variant pushes density and motion further so the remix set feels visually distinct."],
        )
    )

    for layout_mode, art_direction, variant_navigation_mode, variant_density, variant_motion, variant_confidence, variant_reasons in candidate_specs:
        identity = (best_template, layout_mode, art_direction, variant_density, variant_motion, variant_navigation_mode)
        if identity in used_pairs:
            continue
        used_pairs.add(identity)
        variants.append(
            _make_plan(
                template_key=best_template,
                art_direction=art_direction,
                layout_mode=layout_mode,
                density=variant_density,
                motion_level=variant_motion,
                industry=industry,
                vibe=vibe,
                keywords=keywords,
                confidence=variant_confidence,
                reasons=variant_reasons,
                template_catalog=template_catalog,
                section_visibility=section_override if isinstance(section_override, dict) else None,
                navigation_mode=variant_navigation_mode,
            )
        )

    while len(variants) < 3:
        variants.append(
            _make_plan(
                template_key=best_template,
                art_direction=best_art,
                layout_mode=best_layout,
                density=density,
                motion_level=motion_level,
                industry=industry,
                vibe=vibe,
                keywords=keywords,
                confidence=confidence,
                reasons=reasons,
                template_catalog=template_catalog,
                navigation_mode=navigation_choice(best_layout, len(variants)),
            )
        )

    return variants[:3]


def build_render_plan(
    user_prompt: str,
    *,
    brief: BriefInput | dict[str, Any] | None = None,
    model: Any | None = None,
    overrides: dict[str, Any] | None = None,
    theme_catalog: dict[str, Any] | None = None,
    template_catalog: dict[str, dict[str, Any]] | None = None,
) -> RenderPlan:
    return build_render_variants(
        user_prompt,
        brief=brief,
        model=model,
        overrides=overrides,
        theme_catalog=theme_catalog,
        template_catalog=template_catalog,
    )[0]


def remix_render_plan(
    plan: RenderPlan,
    *,
    overrides: dict[str, Any] | None = None,
    theme_catalog: dict[str, Any] | None = None,
    template_catalog: dict[str, dict[str, Any]] | None = None,
) -> RenderPlan:
    if theme_catalog is None:
        theme_catalog = {plan.art_direction: {}}
    if template_catalog is None:
        template_catalog = {plan.template_key: {"template_file": plan.template_file}}
    overrides = overrides or {}

    template_key = _resolve_choice(
        overrides.get("template_key"),
        allowed=set(template_catalog.keys()),
        default=plan.template_key,
    )
    art_direction = _resolve_choice(
        overrides.get("art_direction") or overrides.get("theme_key"),
        allowed=set(theme_catalog.keys()),
        default=plan.art_direction,
    )
    layout_choices = set(LAYOUT_LIBRARY.get(template_key, {}).keys())
    layout_mode = _resolve_choice(overrides.get("layout_mode"), allowed=layout_choices, default=plan.layout_mode)
    density = _normalize_density(_coerce_str(overrides.get("density"), plan.density).lower())
    motion_level = _normalize_motion(_coerce_str(overrides.get("motion_level"), plan.motion_level).lower())
    navigation_choices = set(_recipe_for(template_key, layout_mode).get("navigation_modes", list(NAVIGATION_PATTERNS)))
    navigation_mode = _resolve_choice(
        overrides.get("navigation_mode"),
        allowed=navigation_choices,
        default=plan.navigation_mode,
    )
    override_page_slug = _coerce_str(overrides.get("page_slug"), plan.primary_page_slug)
    target_page = plan.page(override_page_slug)
    section_visibility = plan.section_visibility.copy()
    raw_visibility = overrides.get("section_visibility")
    if isinstance(raw_visibility, dict):
        target_visibility = target_page.section_visibility.copy()
        for key, value in raw_visibility.items():
            if key in target_visibility:
                target_visibility[key] = bool(value)
        if target_page.slug == plan.primary_page_slug:
            section_visibility = target_visibility

    remixed = _make_plan(
        template_key=template_key,
        art_direction=art_direction,
        layout_mode=layout_mode,
        density=density,
        motion_level=motion_level,
        industry=plan.industry,
        vibe=plan.vibe,
        keywords=plan.keywords,
        confidence=max(plan.confidence, 0.7),
        reasons=plan.reasons + ["Studio override applied."],
        template_catalog=template_catalog,
        section_visibility=section_visibility,
        navigation_mode=navigation_mode,
    )
    if isinstance(raw_visibility, dict) and target_page.slug != remixed.primary_page_slug:
        remixed_target_page = remixed.page(target_page.slug)
        next_visibility = remixed_target_page.section_visibility.copy()
        for key, value in raw_visibility.items():
            if key in next_visibility:
                next_visibility[key] = bool(value)
        next_pages = [
            replace(page, section_visibility=next_visibility) if page.slug == remixed_target_page.slug else page
            for page in remixed.pages
        ]
        remixed = replace(remixed, pages=next_pages)
    return replace(remixed, keywords=plan.keywords[:8])
