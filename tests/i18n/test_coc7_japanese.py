from pathlib import Path

import yaml

from core.rulepacks import load_rulepack


def test_coc7_japanese_vocabulary_and_presentation():
    pack = load_rulepack("coc7")

    assert pack.resolve_skill("目星") == "侦查"
    assert pack.resolve_skill("聞き耳") == "聆听"
    assert pack.resolve_skill("図書館") == "图书馆"
    assert pack.resolve_skill("正気度") == "理智"
    assert pack.resolve_skill("応急手当") == "急救"
    assert pack.resolve_skill("クトゥルフ神話") == "克苏鲁神话"

    assert pack.display_name("侦查", "ja") == "目星"
    assert pack.display_name("聆听", "ja") == "聞き耳"
    assert pack.display_name("克苏鲁神话", "ja") == "クトゥルフ神話"
    assert pack.rank_label("crit", "ja") == "クリティカル成功"
    assert pack.rank_label("extreme", "ja") == "イクストリーム成功"
    assert pack.rank_label("hard", "ja") == "ハード成功"
    assert pack.rank_label("regular", "ja") == "レギュラー成功"
    assert pack.rank_label("fumble", "ja") == "ファンブル"


def test_coc7_japanese_difficulty_words_are_declared():
    root = Path(__file__).resolve().parents[2]
    data = yaml.safe_load((root / "rulepacks" / "coc7.yaml").read_text(encoding="utf-8"))
    difficulties = data["resolution"]["difficulties"]

    assert difficulties["regular"]["prefixes"]["ja"] == ["レギュラー"]
    assert difficulties["hard"]["prefixes"]["ja"] == ["ハード"]
    assert difficulties["extreme"]["prefixes"]["ja"] == ["イクストリーム", "エクストリーム"]
    assert difficulties["critical"]["prefixes"]["ja"] == ["クリティカル"]


def test_coc7_existing_english_and_chinese_vocabulary_stays_compatible():
    pack = load_rulepack("coc7")

    assert pack.resolve_skill("spot hidden") == "侦查"
    assert pack.resolve_skill("侦察") == "侦查"
    assert pack.display_name("侦查", "en") == "Spot Hidden"
    assert pack.rank_label("hard", "zh") == "困难成功"
