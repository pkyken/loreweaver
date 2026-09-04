import base64
import json
import time

import httpx
import pytest

from infra.config import ImageGenSettings, Settings
from infra.imagegen import (
    COMFYUI_API_BASE_URL,
    COMFYUI_DEFAULT_MODEL,
    COMFYUI_REFERENCE_MODEL,
    COMFYUI_REFERENCE_TEXT_ENCODER,
    COMFYUI_REFERENCE_VAE,
    IMAGEGEN_PRESETS,
    ComfyUIImageGen,
    ImageGenError,
    OpenAICompatImageGen,
    build_imagegen,
)
from infra.oauth_flows import XAI_API_BASE, XAI_DEFAULT_IMAGE_MODEL, SubscriptionToken
from infra.runtime_config import CredentialBook
from infra.store import Store


async def test_openai_compat_imagegen_posts_expected_shape_and_decodes_b64():
    image_bytes = b"png-bytes"
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["json"] = request.read()
        return httpx.Response(200, json={"data": [{"b64_json": base64.b64encode(image_bytes).decode("ascii")}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gen = OpenAICompatImageGen(
        ImageGenSettings(provider="openai", base_url="https://example.test/v1", api_key="secret", model="img"),
        client=client,
    )
    try:
        data, mime = await gen.generate("a portrait", size="512x512")
    finally:
        await client.aclose()

    assert data == image_bytes
    assert mime == "image/png"
    assert seen["url"] == "https://example.test/v1/images/generations"
    assert seen["auth"] == "Bearer secret"
    assert b'"model":"img"' in seen["json"]
    assert b'"response_format":"b64_json"' in seen["json"]


async def test_openai_compat_imagegen_uses_magic_bytes_before_declared_mime():
    image_bytes = b"\xff\xd8\xff\xe0jpeg"
    client = httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "b64_json": base64.b64encode(image_bytes).decode("ascii"),
                            "mime_type": "image/png",
                        }
                    ]
                },
            )
        )
    )
    gen = OpenAICompatImageGen(
        ImageGenSettings(provider="openai", api_key="secret", model="img"),
        client=client,
    )
    try:
        data, mime = await gen.generate("a portrait")
    finally:
        await client.aclose()

    assert data == image_bytes
    assert mime == "image/jpeg"


async def test_token_provider_preferred_over_api_key():
    seen = {}

    async def provider() -> str:
        return "oauth-bearer"

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"data": [{"b64_json": base64.b64encode(b"x").decode("ascii")}]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gen = OpenAICompatImageGen(
        ImageGenSettings(provider="supergrok", base_url=XAI_API_BASE, api_key="static-key", model="grok-imagine-image"),
        client=client,
        token_provider=provider,
    )
    try:
        await gen.generate("a scene")
    finally:
        await client.aclose()
    assert seen["auth"] == "Bearer oauth-bearer"


async def test_supergrok_uses_xai_dimensions_instead_of_openai_size():
    seen = {}

    async def provider() -> str:
        return "oauth-bearer"

    def handler(request: httpx.Request) -> httpx.Response:
        seen["json"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={"data": [{"b64_json": base64.b64encode(b"x").decode("ascii")}]},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gen = OpenAICompatImageGen(
        ImageGenSettings(
            provider="supergrok",
            base_url=XAI_API_BASE,
            model="grok-imagine-image",
        ),
        client=client,
        token_provider=provider,
    )
    try:
        await gen.generate("a landscape", size="1792x1024")
    finally:
        await client.aclose()

    assert "size" not in seen["json"]
    assert seen["json"]["aspect_ratio"] == "16:9"
    assert seen["json"]["resolution"] == "2k"


async def test_supergrok_preset_build_uses_llm_subscription():
    store = Store(":memory:")
    book = CredentialBook(store)
    await book.save_subscription(
        "supergrok",
        SubscriptionToken("gat", "grt", time.time() + 3600),
    )
    settings = Settings(
        imagegen=ImageGenSettings(provider="supergrok", base_url="https://stale-proxy.example/v1")
    )
    gen = build_imagegen(settings, llm_credentials=book)
    assert gen is not None
    assert isinstance(gen, OpenAICompatImageGen)
    assert gen._settings.model == XAI_DEFAULT_IMAGE_MODEL
    assert gen._settings.base_url == XAI_API_BASE
    assert gen._token_provider is not None
    assert IMAGEGEN_PRESETS["supergrok"]["model"] == XAI_DEFAULT_IMAGE_MODEL


async def test_openai_compat_imagegen_maps_bad_response_to_error_code():
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _request: httpx.Response(200, json={"data": [{}]})))
    gen = OpenAICompatImageGen(
        ImageGenSettings(provider="openai", base_url="https://example.test/v1", api_key="secret", model="img"),
        client=client,
    )
    try:
        with pytest.raises(ImageGenError) as exc:
            await gen.generate("bad")
    finally:
        await client.aclose()

    assert exc.value.code == "imagegen_bad_response"


async def test_openai_compat_imagegen_maps_http_failure_to_error_code():
    client = httpx.AsyncClient(transport=httpx.MockTransport(lambda _request: httpx.Response(500, text="nope")))
    gen = OpenAICompatImageGen(
        ImageGenSettings(provider="openai", base_url="https://example.test/v1", api_key="secret", model="img"),
        client=client,
    )
    try:
        with pytest.raises(ImageGenError) as exc:
            await gen.generate("bad")
    finally:
        await client.aclose()

    assert exc.value.code == "imagegen_http_error"


def test_build_imagegen_returns_none_when_incomplete():
    # An explicit empty block, not the developer's .env: "incomplete" is what is under test.
    assert build_imagegen(Settings(imagegen=ImageGenSettings())) is None
    assert build_imagegen(Settings(imagegen=ImageGenSettings(provider="openai", model="img"))) is None


async def test_comfyui_imagegen_queues_z_image_workflow_and_downloads_history_output():
    image_bytes = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000d49444154789c6360f8ffff3f0005fe02fea7a0a5810000000049454e44ae426082"
    )
    seen: dict[str, object] = {}
    history_calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal history_calls
        path = request.url.path
        if path == "/prompt":
            body = json.loads(request.content)
            seen["workflow"] = body["prompt"]
            return httpx.Response(200, json={"prompt_id": "job-1", "number": 1, "node_errors": {}})
        if path == "/history/job-1":
            history_calls += 1
            if history_calls == 1:
                return httpx.Response(200, json={})
            return httpx.Response(
                200,
                json={
                    "job-1": {
                        "status": {"status_str": "success", "completed": True},
                        "outputs": {
                            "9": {
                                "images": [{"filename": "loreweaver_00001_.png", "subfolder": "", "type": "output"}]
                            }
                        },
                    }
                },
            )
        if path == "/view":
            seen["view_params"] = dict(request.url.params)
            return httpx.Response(200, content=image_bytes, headers={"content-type": "image/png"})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gen = ComfyUIImageGen(
        ImageGenSettings(provider="comfyui", base_url=COMFYUI_API_BASE_URL, model=COMFYUI_DEFAULT_MODEL),
        client=client,
        poll_interval=0,
        seed_factory=lambda: 123,
    )
    try:
        data, mime = await gen.generate("a moonlit ruined church", size="513x769")
    finally:
        await client.aclose()

    workflow = seen["workflow"]
    assert isinstance(workflow, dict)
    assert workflow["27"]["inputs"]["text"] == "a moonlit ruined church"
    assert workflow["13"]["inputs"] == {"width": 512, "height": 768, "batch_size": 1}
    assert workflow["28"]["inputs"]["unet_name"] == COMFYUI_DEFAULT_MODEL
    assert workflow["30"]["inputs"]["clip_name"] == "qwen_3_4b_fp4_mixed.safetensors"
    assert workflow["3"]["inputs"]["seed"] == 123
    assert seen["view_params"] == {
        "filename": "loreweaver_00001_.png",
        "type": "output",
    }
    assert data == image_bytes
    assert mime == "image/png"


async def test_comfyui_imagegen_uploads_reference_and_queues_qwen_edit_workflow():
    image_bytes = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000d49444154789c6360f8ffff3f0005fe02fea7a0a5810000000049454e44ae426082"
    )
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/upload/image":
            seen["upload_body"] = request.content
            return httpx.Response(
                200,
                json={"name": "loreweaver-reference.png", "subfolder": "refs", "type": "input"},
            )
        if path == "/prompt":
            seen["workflow"] = json.loads(request.content)["prompt"]
            return httpx.Response(200, json={"prompt_id": "qwen-job", "node_errors": {}})
        if path == "/history/qwen-job":
            return httpx.Response(
                200,
                json={
                    "qwen-job": {
                        "status": {"status_str": "success", "completed": True},
                        "outputs": {
                            "13": {
                                "images": [
                                    {"filename": "loreweaver-qwen-edit_00001_.png", "type": "output"}
                                ]
                            }
                        },
                    }
                },
            )
        if path == "/view":
            seen["view_params"] = dict(request.url.params)
            return httpx.Response(200, content=image_bytes, headers={"content-type": "image/png"})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gen = ComfyUIImageGen(
        ImageGenSettings(provider="comfyui", base_url=COMFYUI_API_BASE_URL, model=COMFYUI_DEFAULT_MODEL),
        client=client,
        poll_interval=0,
        seed_factory=lambda: 456,
    )
    try:
        data, mime = await gen.generate(
            "a woman standing on a rainy quay",
            size="512x512",
            reference=image_bytes,
            reference_mime="image/png",
        )
    finally:
        await client.aclose()

    workflow = seen["workflow"]
    assert isinstance(workflow, dict)
    assert workflow["1"]["inputs"]["image"] == "refs/loreweaver-reference.png"
    assert workflow["3"]["inputs"]["clip_name"] == COMFYUI_REFERENCE_TEXT_ENCODER
    assert workflow["4"]["inputs"]["vae_name"] == COMFYUI_REFERENCE_VAE
    assert workflow["5"]["inputs"]["unet_name"] == COMFYUI_REFERENCE_MODEL
    assert workflow["8"]["inputs"]["prompt"] == "a woman standing on a rainy quay"
    assert workflow["8"]["inputs"]["image1"] == ["2", 0]
    assert workflow["11"]["inputs"]["seed"] == 456
    assert b"loreweaver-reference-" in seen["upload_body"]
    assert seen["view_params"] == {"filename": "loreweaver-qwen-edit_00001_.png", "type": "output"}
    assert data == image_bytes
    assert mime == "image/png"


async def test_comfyui_imagegen_reports_execution_errors_and_does_not_require_an_api_key():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/prompt":
            return httpx.Response(200, json={"prompt_id": "job-error"})
        return httpx.Response(
            200,
            json={
                "job-error": {
                    "status": {"status_str": "error", "completed": True, "messages": ["missing model"]},
                    "outputs": {},
                }
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gen = ComfyUIImageGen(
        ImageGenSettings(provider="comfyui", base_url=COMFYUI_API_BASE_URL, model="z-image.safetensors"),
        client=client,
        poll_interval=0,
    )
    try:
        with pytest.raises(ImageGenError) as exc:
            await gen.generate("test")
    finally:
        await client.aclose()

    assert exc.value.code == "imagegen_http_error"


def test_build_imagegen_uses_local_comfyui_without_an_api_key():
    gen = build_imagegen(Settings(imagegen=ImageGenSettings(provider="comfyui")))

    assert isinstance(gen, ComfyUIImageGen)
    assert gen._settings.base_url == COMFYUI_API_BASE_URL
    assert gen._settings.model == COMFYUI_DEFAULT_MODEL
    assert IMAGEGEN_PRESETS["comfyui"]["model"] == COMFYUI_DEFAULT_MODEL
