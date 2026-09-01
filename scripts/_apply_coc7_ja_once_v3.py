from __future__ import annotations

from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "scripts" / "_apply_coc7_ja_once_v2.py"
TEST = ROOT / "tests" / "i18n" / "test_coc7_japanese.py"

if V2.exists():
    runpy.run_path(str(V2), run_name="__main__")

TEST.write_text(
    '''from pathlib import Path\n\nimport yaml\n\nfrom core.rulepacks import load_rulepack\n\n\ndef test_coc7_japanese_vocabulary_and_presentation():\n    pack = load_rulepack("coc7")\n\n    assert pack.resolve_skill("目星") == "侦查"\n    assert pack.resolve_skill("聞き耳") == "聆听"\n    assert pack.resolve_skill("図書館") == "图书馆"\n    assert pack.resolve_skill("正気度") == "理智"\n    assert pack.resolve_skill("応急手当") == "急救"\n    assert pack.resolve_skill("クトゥルフ神話") == "克苏鲁神话"\n\n    assert pack.display_name("侦查", "ja") == "目星"\n    assert pack.display_name("聆听", "ja") == "聞き耳"\n    assert pack.display_name("克苏鲁神话", "ja") == "クトゥルフ神話"\n    assert pack.rank_label("crit", "ja") == "クリティカル成功"\n    assert pack.rank_label("extreme", "ja") == "イクストリーム成功"\n    assert pack.rank_label("hard", "ja") == "ハード成功"\n    assert pack.rank_label("regular", "ja") == "レギュラー成功"\n    assert pack.rank_label("fumble", "ja") == "ファンブル"\n\n\ndef test_coc7_japanese_difficulty_words_are_declared():\n    root = Path(__file__).resolve().parents[2]\n    data = yaml.safe_load((root / "rulepacks" / "coc7.yaml").read_text(encoding="utf-8"))\n    difficulties = data["resolution"]["difficulties"]\n\n    assert difficulties["regular"]["prefixes"]["ja"] == ["レギュラー"]\n    assert difficulties["hard"]["prefixes"]["ja"] == ["ハード"]\n    assert difficulties["extreme"]["prefixes"]["ja"] == ["イクストリーム", "エクストリーム"]\n    assert difficulties["critical"]["prefixes"]["ja"] == ["クリティカル"]\n\n\ndef test_coc7_existing_english_and_chinese_vocabulary_stays_compatible():\n    pack = load_rulepack("coc7")\n\n    assert pack.resolve_skill("spot hidden") == "侦查"\n    assert pack.resolve_skill("侦察") == "侦查"\n    assert pack.display_name("侦查", "en") == "Spot Hidden"\n    assert pack.rank_label("hard", "zh") == "困难成功"\n''',
    encoding="utf-8",
)
