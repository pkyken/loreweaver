from infra.config import Settings


def test_settings_can_load_env_file_from_trpg_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("TRPG_LOCALE", raising=False)
    monkeypatch.delenv("TRPG_DATA_DIR", raising=False)
    env_file = tmp_path / "server.env"
    env_file.write_text("TRPG_LOCALE=zh\nTRPG_DATA_DIR=/srv/loreweaver-data\n", encoding="utf-8")
    monkeypatch.setenv("TRPG_ENV_FILE", str(env_file))

    settings = Settings()

    assert settings.locale == "zh"
    assert settings.data_dir == "/srv/loreweaver-data"


def test_explicit_env_file_overrides_trpg_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("TRPG_LOCALE", raising=False)
    env_file = tmp_path / "server.env"
    explicit = tmp_path / "explicit.env"
    env_file.write_text("TRPG_LOCALE=zh\n", encoding="utf-8")
    explicit.write_text("TRPG_LOCALE=en\n", encoding="utf-8")
    monkeypatch.setenv("TRPG_ENV_FILE", str(env_file))

    settings = Settings(_env_file=str(explicit))

    assert settings.locale == "en"


def test_settings_can_load_comfyui_imagegen_from_env_file(tmp_path, monkeypatch):
    for name in (
        "TRPG_IMAGEGEN__PROVIDER",
        "TRPG_IMAGEGEN__BASE_URL",
        "TRPG_IMAGEGEN__MODEL",
        "TRPG_IMAGEGEN__SIZE",
    ):
        monkeypatch.delenv(name, raising=False)
    env_file = tmp_path / "server.env"
    env_file.write_text(
        "\n".join(
            (
                "TRPG_IMAGEGEN__PROVIDER=comfyui",
                "TRPG_IMAGEGEN__BASE_URL=http://127.0.0.1:8188",
                "TRPG_IMAGEGEN__MODEL=z_image_turbo_nvfp4.safetensors",
                "TRPG_IMAGEGEN__SIZE=512x512",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TRPG_ENV_FILE", str(env_file))

    settings = Settings()

    assert settings.imagegen.provider == "comfyui"
    assert settings.imagegen.base_url == "http://127.0.0.1:8188"
    assert settings.imagegen.model == "z_image_turbo_nvfp4.safetensors"
    assert settings.imagegen.size == "512x512"
