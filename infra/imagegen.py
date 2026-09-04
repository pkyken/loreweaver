"""Image generation over OpenAI-compatible and local ComfyUI HTTP APIs.

Providers use ``/images/generations`` without native SDKs. Small wire-level
differences, such as xAI's aspect-ratio/resolution fields, are translated here
so runtime switching remains deterministic and testable offline. ComfyUI uses
its native ``/prompt`` + ``/history`` + ``/view`` API with built-in
Z-Image-Turbo text-to-image and Qwen Image Edit reference-image graphs.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import math
import secrets
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Protocol
from urllib.parse import quote

import httpx

from infra.config import ImageGenSettings, Settings
from infra.oauth_flows import XAI_API_BASE, XAI_DEFAULT_IMAGE_MODEL

if TYPE_CHECKING:
    from infra.runtime_config import CredentialBook

OPENAI_IMAGE_BASE_URL = "https://api.openai.com/v1"
COMFYUI_API_BASE_URL = "http://127.0.0.1:8188"
COMFYUI_DEFAULT_MODEL = "z_image_turbo_nvfp4.safetensors"
COMFYUI_DEFAULT_TEXT_ENCODER = "qwen_3_4b_fp4_mixed.safetensors"
COMFYUI_DEFAULT_VAE = "ae.safetensors"
# The reference-image lane follows ComfyUI's bundled Qwen Image Edit 2509 graph.
# Keep it separate from the Z-Image model setting: one deployment can use both lanes.
COMFYUI_REFERENCE_MODEL = "qwen_image_edit_2509_fp8_e4m3fn.safetensors"
COMFYUI_REFERENCE_TEXT_ENCODER = "qwen_2.5_vl_7b_fp8_scaled.safetensors"
COMFYUI_REFERENCE_VAE = "qwen_image_vae.safetensors"
IMAGEGEN_OVERRIDE_FIELDS: tuple[str, ...] = ("provider", "base_url", "api_key", "model", "size")

# Provider presets: base_url + default model. ``supergrok`` reuses the SuperGrok
# subscription token from the LLM credential book (not a separate image key).
IMAGEGEN_PRESETS: dict[str, dict[str, str]] = {
    "openai": {"base_url": OPENAI_IMAGE_BASE_URL, "model": "gpt-image-1"},
    "supergrok": {"base_url": XAI_API_BASE, "model": XAI_DEFAULT_IMAGE_MODEL},
    # The NVFP4 + mixed-FP4 defaults are the practical local starting point for
    # a 16 GB Blackwell card. The model field remains editable for BF16/INT8
    # installs or a custom ComfyUI model search path.
    "comfyui": {"base_url": COMFYUI_API_BASE_URL, "model": COMFYUI_DEFAULT_MODEL},
}

TokenProvider = Callable[[], Awaitable[str]]
SeedFactory = Callable[[], int]

_PNG_1X1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360f8ffff3f0005fe02fea7a0a5810000000049454e44ae426082"
)

_XAI_ASPECT_RATIOS: tuple[tuple[str, float], ...] = (
    ("1:1", 1.0),
    ("16:9", 16 / 9),
    ("9:16", 9 / 16),
    ("4:3", 4 / 3),
    ("3:4", 3 / 4),
    ("3:2", 3 / 2),
    ("2:3", 2 / 3),
    ("2:1", 2.0),
    ("1:2", 0.5),
    ("19.5:9", 19.5 / 9),
    ("9:19.5", 9 / 19.5),
    ("20:9", 20 / 9),
    ("9:20", 9 / 20),
)


class ImageGenError(RuntimeError):
    """Stable image-generation error code plus optional detail."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code


class ImageGen(Protocol):
    async def generate(
        self,
        prompt: str,
        *,
        size: str = "1024x1024",
        reference: bytes | None = None,
        reference_mime: str = "",
    ) -> tuple[bytes, str]:
        """Generate one image. Returns ``(bytes, mime)``.

        ``reference`` is an optional 定妆 reference image (M19): consistency across a
        module's art is the hard part, so the Stage Director sends the author's fixed
        portrait with every request. Providers that expose an image-edit endpoint
        condition on it; the rest ignore it and fall back to prompt-only generation —
        the structural half of the discipline (no reference → no portrait) is enforced
        by the caller regardless.
        """


class OpenAICompatImageGen:
    """HTTP client for OpenAI-compatible image generation endpoints."""

    def __init__(
        self,
        settings: ImageGenSettings,
        *,
        client: httpx.AsyncClient | None = None,
        token_provider: TokenProvider | None = None,
        timeout: float = 120.0,
    ) -> None:
        self._settings = settings
        self._client = client
        self._token_provider = token_provider
        self._timeout = timeout

    async def generate(
        self,
        prompt: str,
        *,
        size: str = "1024x1024",
        reference: bytes | None = None,
        reference_mime: str = "",
    ) -> tuple[bytes, str]:
        prompt = str(prompt or "").strip()
        if not prompt:
            raise ImageGenError("imagegen_bad_prompt")
        if not self._settings.model or not self._settings.provider:
            raise ImageGenError("imagegen_not_configured")
        if self._token_provider is not None:
            api_key = await self._token_provider()
        else:
            api_key = self._settings.api_key
        if not api_key:
            raise ImageGenError("imagegen_missing_key")

        close_client = False
        client = self._client
        if client is None:
            client = httpx.AsyncClient(timeout=self._timeout)
            close_client = True
        requested_size = size or self._settings.size or "1024x1024"
        request_body = {
            "model": self._settings.model,
            "prompt": prompt,
            "response_format": "b64_json",
        }
        if (self._settings.provider or "").casefold() == "supergrok":
            # xAI's Imagine API uses aspect_ratio + 1k/2k resolution rather
            # than OpenAI's pixel-based `size` field.
            request_body.update(_xai_dimensions(requested_size))
        else:
            request_body["size"] = requested_size

        base = _base_url(self._settings).rstrip("/")
        try:
            if reference:
                # A 定妆 reference means image-to-image, which is a DIFFERENT endpoint
                # and a multipart body on the OpenAI-compatible surface. `response_format`
                # is not accepted there; edits answer b64 by default.
                request_body.pop("response_format", None)
                response = await client.post(
                    f"{base}/images/edits",
                    headers={"Authorization": f"Bearer {api_key}"},
                    data={key: str(value) for key, value in request_body.items()},
                    files={"image": ("reference.png", reference, reference_mime or "image/png")},
                )
            else:
                response = await client.post(
                    f"{base}/images/generations",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=request_body,
                )
        except httpx.TimeoutException as exc:
            raise ImageGenError("imagegen_timeout") from exc
        except httpx.HTTPError as exc:
            raise ImageGenError("imagegen_http_error") from exc
        finally:
            if close_client:
                await client.aclose()

        if response.status_code < 200 or response.status_code >= 300:
            raise ImageGenError("imagegen_http_error", str(response.status_code))

        try:
            payload = response.json()
            entry = payload["data"][0]
            b64 = entry["b64_json"]
            data = base64.b64decode(str(b64), validate=True)
        except (KeyError, IndexError, TypeError, ValueError, binascii.Error) as exc:
            raise ImageGenError("imagegen_bad_response") from exc
        if not data:
            raise ImageGenError("imagegen_bad_response")
        declared_mime = entry.get("mime_type") if isinstance(entry, dict) else None
        return data, _detect_image_mime(data, declared_mime)


class ComfyUIImageGen:
    """Generate images through a local ComfyUI server.

    Prompt-only jobs use the bundled Z-Image-Turbo graph. Jobs with a reference
    image use the bundled Qwen Image Edit 2509 graph and upload the reference to
    ComfyUI's input directory first. Both lanes finish through the same
    ``/prompt`` + ``/history`` + ``/view`` API path.
    """

    def __init__(
        self,
        settings: ImageGenSettings,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = 300.0,
        poll_interval: float = 0.25,
        seed_factory: SeedFactory | None = None,
    ) -> None:
        self._settings = settings
        self._client = client
        self._timeout = timeout
        self._poll_interval = max(0.0, poll_interval)
        self._seed_factory = seed_factory or _comfy_seed

    async def generate(
        self,
        prompt: str,
        *,
        size: str = "1024x1024",
        reference: bytes | None = None,
        reference_mime: str = "",
    ) -> tuple[bytes, str]:
        prompt = str(prompt or "").strip()
        if not prompt:
            raise ImageGenError("imagegen_bad_prompt")
        if (self._settings.provider or "").casefold() != "comfyui" or not self._settings.model:
            raise ImageGenError("imagegen_not_configured")

        base = _base_url(self._settings).rstrip("/")
        if not base:
            raise ImageGenError("imagegen_not_configured")

        close_client = False
        client = self._client
        if client is None:
            client = httpx.AsyncClient(timeout=self._timeout)
            close_client = True
        headers = _comfy_headers(self._settings.api_key)
        try:
            if reference:
                reference_image = await _upload_comfy_reference(
                    client,
                    base,
                    headers,
                    reference,
                    reference_mime,
                )
                workflow = _qwen_image_edit_workflow(
                    prompt,
                    reference_image=reference_image,
                    seed=int(self._seed_factory()),
                )
            else:
                width, height = _comfy_dimensions(size or self._settings.size or "1024x1024")
                workflow = _z_image_turbo_workflow(
                    prompt,
                    width=width,
                    height=height,
                    model=self._settings.model,
                    seed=int(self._seed_factory()),
                )
            return await _run_comfy_workflow(
                client,
                base,
                headers,
                workflow,
                timeout=self._timeout,
                poll_interval=self._poll_interval,
            )
        finally:
            if close_client:
                await client.aclose()


class FakeImageGen:
    """Deterministic offline image generator for tests.

    Records whether a 定妆 reference rode along (`calls[i]["reference"]` is its byte
    length as a string, `"0"` for a prompt-only request), so the M19 image discipline
    is testable without a provider."""

    def __init__(self, data: bytes = _PNG_1X1, mime: str = "image/png") -> None:
        self.data = data
        self.mime = mime
        self.calls: list[dict[str, str]] = []

    async def generate(
        self,
        prompt: str,
        *,
        size: str = "1024x1024",
        reference: bytes | None = None,
        reference_mime: str = "",
    ) -> tuple[bytes, str]:
        self.calls.append(
            {
                "prompt": str(prompt),
                "size": str(size),
                "reference": str(len(reference or b"")),
                "reference_mime": reference_mime,
            }
        )
        return self.data, self.mime


def build_imagegen(
    settings: Settings,
    *,
    llm_credentials: CredentialBook | None = None,
) -> ImageGen | None:
    """Build the configured image generator, or ``None`` when incomplete.

    For ``supergrok``, credentials come from the LLM SuperGrok subscription
    (same token as chat) — no separate imagegen key is required.
    """
    cfg = _apply_imagegen_preset(settings.imagegen)
    provider = (cfg.provider or "").casefold()

    if provider == "supergrok":
        return _build_supergrok_imagegen(cfg, llm_credentials=llm_credentials)

    if provider == "comfyui":
        if not cfg.model:
            return None
        return ComfyUIImageGen(cfg)

    if not cfg.provider or not cfg.model or not cfg.api_key:
        return None
    return OpenAICompatImageGen(cfg)


def _build_supergrok_imagegen(
    cfg: ImageGenSettings,
    *,
    llm_credentials: CredentialBook | None,
) -> ImageGen | None:
    if llm_credentials is None:
        return None
    manager = llm_credentials.subscription_manager_sync("supergrok")
    if manager is None:
        return None
    filled = cfg.model_copy(
        update={
            "provider": "supergrok",
            # Subscription tokens must never be sent to a remembered proxy.
            "base_url": XAI_API_BASE,
            "model": cfg.model or XAI_DEFAULT_IMAGE_MODEL,
            "api_key": "",  # token_provider supplies the bearer
        }
    )
    return OpenAICompatImageGen(filled, token_provider=manager.access_token)


def _apply_imagegen_preset(cfg: ImageGenSettings) -> ImageGenSettings:
    provider = (cfg.provider or "").casefold()
    preset = IMAGEGEN_PRESETS.get(provider)
    if not preset:
        return cfg
    updates: dict[str, str] = {}
    if not cfg.base_url:
        updates["base_url"] = preset["base_url"]
    if not cfg.model:
        updates["model"] = preset["model"]
    return cfg.model_copy(update=updates) if updates else cfg


def apply_imagegen_overrides(base: Settings, overrides: dict) -> Settings:
    filtered = {
        key: value
        for key, value in (overrides or {}).items()
        if key in IMAGEGEN_OVERRIDE_FIELDS and value is not None
    }
    if not filtered:
        return base.model_copy(deep=True)
    return base.model_copy(update={"imagegen": base.imagegen.model_copy(update=filtered)})


def describe_imagegen_settings(settings: ImageGenSettings, *, configured: bool = False) -> dict[str, object]:
    filled = _apply_imagegen_preset(settings)
    has_key = bool(filled.api_key) or (filled.provider or "").casefold() == "supergrok" and configured
    return {
        "provider": filled.provider,
        "base_url": _base_url(filled) if filled.provider else filled.base_url,
        "model": filled.model,
        "size": filled.size,
        "api_key_masked": mask_secret_tail(filled.api_key),
        "has_key": has_key,
        "configured": configured,
    }


def mask_secret_tail(value: str) -> str:
    if not value:
        return ""
    tail = value[-4:]
    return f"{'*' * max(4, len(value) - 4)}{tail}"


def _base_url(settings: ImageGenSettings) -> str:
    if settings.base_url:
        return settings.base_url
    provider = (settings.provider or "").casefold()
    preset = IMAGEGEN_PRESETS.get(provider)
    if preset:
        return preset["base_url"]
    if provider == "openai":
        return OPENAI_IMAGE_BASE_URL
    return settings.base_url


def _comfy_seed() -> int:
    return secrets.randbelow(2**63 - 1)


def _comfy_dimensions(size: str) -> tuple[int, int]:
    try:
        width_raw, height_raw = str(size).casefold().split("x", 1)
        width, height = int(width_raw), int(height_raw)
        if width <= 0 or height <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return 1024, 1024
    # EmptySD3LatentImage requires dimensions aligned to the latent stride. Keep
    # direct callers safe even when they bypass the admin frame's size validator.
    width = max(128, min(4096, width)) // 8 * 8
    height = max(128, min(4096, height)) // 8 * 8
    return width, height


def _z_image_turbo_workflow(
    prompt: str,
    *,
    width: int,
    height: int,
    model: str,
    seed: int,
) -> dict[str, dict[str, object]]:
    """Return ComfyUI API-format nodes for the bundled Z-Image-Turbo graph."""
    return {
        "30": {
            "inputs": {
                "clip_name": COMFYUI_DEFAULT_TEXT_ENCODER,
                "type": "lumina2",
                "device": "default",
            },
            "class_type": "CLIPLoader",
        },
        "29": {"inputs": {"vae_name": COMFYUI_DEFAULT_VAE}, "class_type": "VAELoader"},
        "33": {"inputs": {"conditioning": ["27", 0]}, "class_type": "ConditioningZeroOut"},
        "8": {
            "inputs": {"samples": ["3", 0], "vae": ["29", 0]},
            "class_type": "VAEDecode",
        },
        "28": {
            "inputs": {"unet_name": model, "weight_dtype": "default"},
            "class_type": "UNETLoader",
        },
        "27": {
            "inputs": {"clip": ["30", 0], "text": prompt},
            "class_type": "CLIPTextEncode",
        },
        "13": {
            "inputs": {"width": width, "height": height, "batch_size": 1},
            "class_type": "EmptySD3LatentImage",
        },
        "11": {
            "inputs": {"model": ["28", 0], "shift": 3},
            "class_type": "ModelSamplingAuraFlow",
        },
        "3": {
            "inputs": {
                "model": ["11", 0],
                "positive": ["27", 0],
                "negative": ["33", 0],
                "latent_image": ["13", 0],
                "seed": seed,
                "steps": 8,
                "cfg": 1,
                "sampler_name": "res_multistep",
                "scheduler": "simple",
                "denoise": 1,
            },
            "class_type": "KSampler",
        },
        "9": {
            "inputs": {"filename_prefix": "loreweaver", "images": ["8", 0]},
            "class_type": "SaveImage",
        },
    }


def _qwen_image_edit_workflow(
    prompt: str,
    *,
    reference_image: str,
    seed: int,
) -> dict[str, dict[str, object]]:
    """Return the minimal one-reference version of ComfyUI's Qwen 2509 graph.

    The bundled template supports three images and an optional Lightning LoRA. The
    Loreweaver lane needs one authored subject reference, so the base 20-step graph
    is enough and avoids making the optional LoRA another installation requirement.
    """
    return {
        "1": {"inputs": {"image": reference_image}, "class_type": "LoadImage"},
        "2": {"inputs": {"image": ["1", 0]}, "class_type": "FluxKontextImageScale"},
        "3": {
            "inputs": {
                "clip_name": COMFYUI_REFERENCE_TEXT_ENCODER,
                "type": "qwen_image",
                "device": "default",
            },
            "class_type": "CLIPLoader",
        },
        "4": {"inputs": {"vae_name": COMFYUI_REFERENCE_VAE}, "class_type": "VAELoader"},
        "5": {
            "inputs": {"unet_name": COMFYUI_REFERENCE_MODEL, "weight_dtype": "default"},
            "class_type": "UNETLoader",
        },
        "6": {
            "inputs": {"model": ["5", 0], "shift": 3},
            "class_type": "ModelSamplingAuraFlow",
        },
        "7": {
            "inputs": {"model": ["6", 0], "strength": 1.0},
            "class_type": "CFGNorm",
        },
        "8": {
            "inputs": {
                "clip": ["3", 0],
                "vae": ["4", 0],
                "image1": ["2", 0],
                "prompt": prompt,
            },
            "class_type": "TextEncodeQwenImageEditPlus",
        },
        "9": {
            "inputs": {
                "clip": ["3", 0],
                "vae": ["4", 0],
                "image1": ["2", 0],
                "prompt": "",
            },
            "class_type": "TextEncodeQwenImageEditPlus",
        },
        "10": {
            "inputs": {"pixels": ["2", 0], "vae": ["4", 0]},
            "class_type": "VAEEncode",
        },
        "11": {
            "inputs": {
                "model": ["7", 0],
                "positive": ["8", 0],
                "negative": ["9", 0],
                "latent_image": ["10", 0],
                "seed": seed,
                "steps": 20,
                "cfg": 4,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1,
            },
            "class_type": "KSampler",
        },
        "12": {"inputs": {"samples": ["11", 0], "vae": ["4", 0]}, "class_type": "VAEDecode"},
        "13": {
            "inputs": {"filename_prefix": "loreweaver-qwen-edit", "images": ["12", 0]},
            "class_type": "SaveImage",
        },
    }


async def _upload_comfy_reference(
    client: httpx.AsyncClient,
    base: str,
    headers: dict[str, str],
    reference: bytes,
    reference_mime: str,
) -> str:
    """Upload one content-addressed reference and return its LoadImage name."""
    mime = _detect_image_mime(reference, reference_mime)
    extension = {"image/jpeg": "jpg", "image/webp": "webp", "image/gif": "gif"}.get(mime, "png")
    digest = hashlib.sha256(reference).hexdigest()[:24]
    filename = f"loreweaver-reference-{digest}.{extension}"
    try:
        response = await client.post(
            f"{base}/upload/image",
            headers=headers,
            data={"type": "input", "overwrite": "true"},
            files={"image": (filename, reference, mime)},
        )
    except httpx.TimeoutException as exc:
        raise ImageGenError("imagegen_timeout") from exc
    except httpx.HTTPError as exc:
        raise ImageGenError("imagegen_http_error") from exc
    _require_success(response)
    try:
        payload = response.json()
        name = str(payload["name"])
        subfolder = str(payload.get("subfolder") or "").strip("/")
    except (KeyError, TypeError, ValueError) as exc:
        raise ImageGenError("imagegen_bad_response") from exc
    if not name:
        raise ImageGenError("imagegen_bad_response")
    return f"{subfolder}/{name}" if subfolder else name


async def _run_comfy_workflow(
    client: httpx.AsyncClient,
    base: str,
    headers: dict[str, str],
    workflow: dict[str, dict[str, object]],
    *,
    timeout: float,
    poll_interval: float,
) -> tuple[bytes, str]:
    """Queue a Comfy graph, await its first image output, and download it."""
    try:
        response = await client.post(f"{base}/prompt", headers=headers, json={"prompt": workflow})
    except httpx.TimeoutException as exc:
        raise ImageGenError("imagegen_timeout") from exc
    except httpx.HTTPError as exc:
        raise ImageGenError("imagegen_http_error") from exc
    _require_success(response)
    try:
        payload = response.json()
        prompt_id = str(payload["prompt_id"])
        node_errors = payload.get("node_errors") or {}
    except (KeyError, TypeError, ValueError) as exc:
        raise ImageGenError("imagegen_bad_response") from exc
    if not prompt_id or node_errors:
        raise ImageGenError("imagegen_http_error", str(node_errors or "missing prompt id"))

    image = None
    deadline = asyncio.get_running_loop().time() + max(0.0, timeout)
    while image is None:
        try:
            history_response = await client.get(
                f"{base}/history/{quote(prompt_id, safe='')}", headers=headers
            )
        except httpx.TimeoutException as exc:
            raise ImageGenError("imagegen_timeout") from exc
        except httpx.HTTPError as exc:
            raise ImageGenError("imagegen_http_error") from exc
        _require_success(history_response)
        try:
            history_payload = history_response.json()
        except (TypeError, ValueError) as exc:
            raise ImageGenError("imagegen_bad_response") from exc
        if not isinstance(history_payload, dict):
            raise ImageGenError("imagegen_bad_response")
        history_entry = history_payload.get(prompt_id)
        if history_entry is not None and not isinstance(history_entry, dict):
            raise ImageGenError("imagegen_bad_response")
        if isinstance(history_entry, dict):
            status = history_entry.get("status")
            status_str = status.get("status_str", "") if isinstance(status, dict) else ""
            if str(status_str).casefold() in {"error", "failed"}:
                raise ImageGenError("imagegen_http_error", _comfy_status_detail(status))
            image = _first_comfy_image(history_entry)
            if image is None and isinstance(status, dict) and status.get("completed"):
                raise ImageGenError("imagegen_bad_response")

        if image is None:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise ImageGenError("imagegen_timeout")
            if poll_interval:
                await asyncio.sleep(min(poll_interval, remaining))

    params = {"filename": image["filename"]}
    if image.get("subfolder"):
        params["subfolder"] = image["subfolder"]
    if image.get("type"):
        params["type"] = image["type"]
    try:
        image_response = await client.get(f"{base}/view", params=params, headers=headers)
    except httpx.TimeoutException as exc:
        raise ImageGenError("imagegen_timeout") from exc
    except httpx.HTTPError as exc:
        raise ImageGenError("imagegen_http_error") from exc
    _require_success(image_response)
    data = image_response.content
    if not data:
        raise ImageGenError("imagegen_bad_response")
    return data, _detect_image_mime(data, image_response.headers.get("content-type"))


def _comfy_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"} if api_key else {}


def _require_success(response: httpx.Response) -> None:
    if response.status_code < 200 or response.status_code >= 300:
        raise ImageGenError("imagegen_http_error", str(response.status_code))


def _first_comfy_image(history_entry: dict[str, object]) -> dict[str, str] | None:
    outputs = history_entry.get("outputs")
    if not isinstance(outputs, dict):
        return None
    for node_output in outputs.values():
        if not isinstance(node_output, dict):
            continue
        images = node_output.get("images")
        if not isinstance(images, list):
            continue
        for image in images:
            if not isinstance(image, dict) or not image.get("filename"):
                continue
            return {
                "filename": str(image["filename"]),
                "subfolder": str(image.get("subfolder") or ""),
                "type": str(image.get("type") or "output"),
            }
    return None


def _comfy_status_detail(status: object) -> str:
    if not isinstance(status, dict):
        return "ComfyUI execution failed"
    messages = status.get("messages")
    if isinstance(messages, list):
        return " ".join(str(item) for item in messages)[-500:]
    return str(status.get("status_str") or "ComfyUI execution failed")


def _detect_image_mime(data: bytes, declared: object = None) -> str:
    """Return the actual image MIME from magic bytes, then a safe declaration."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if isinstance(declared, str) and declared.casefold() in {
        "image/gif",
        "image/jpeg",
        "image/png",
        "image/webp",
    }:
        return declared.casefold()
    # Preserve compatibility with providers that omit MIME metadata.
    return "image/png"


def _xai_dimensions(size: str) -> dict[str, str]:
    """Translate a pixel size to xAI Imagine's nearest supported dimensions."""
    try:
        width_raw, height_raw = str(size).casefold().split("x", 1)
        width, height = int(width_raw), int(height_raw)
        if width <= 0 or height <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return {"aspect_ratio": "1:1", "resolution": "1k"}

    ratio = width / height
    # Log distance treats portrait and landscape deviations symmetrically.
    aspect_ratio = min(
        _XAI_ASPECT_RATIOS,
        key=lambda item: abs(math.log(ratio / item[1])),
    )[0]
    return {
        "aspect_ratio": aspect_ratio,
        "resolution": "2k" if max(width, height) > 1024 else "1k",
    }
