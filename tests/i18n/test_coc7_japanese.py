from core.rulepacks import load_rulepack


def test_coc7_japanese_pack_preserves_base_and_resolves_japanese_terms():
    pack = load_rulepack("coc7-ja")

    assert pack.system == "coc7-ja"
    assert pack.defaults["侦查"] == 25
    assert pack.commands["ra"].action == "check"
    assert pack.sheet_spec is not None
    assert pack.sheet_spec.label == "CoC 7版（日本語）"

    expected = {
        "目星": "侦查",
        "聞き耳": "聆听",
        "図書館": "图书馆",
        "応急手当": "急救",
        "言いくるめ": "话术",
        "威圧": "恐吓",
        "説得": "说服",
        "正気度": "理智",
        "回避": "闪避",
        "クトゥルフ神話": "克苏鲁神话",
    }
    for term, canonical in expected.items():
        assert pack.resolve_skill(term) == canonical


def test_coc7_japanese_pack_exposes_localized_labels_and_commands():
    pack = load_rulepack("クトゥルフ神話TRPG")

    assert pack.display_name("侦查", "ja-JP") == "目星"
    assert pack.display_name("聆听", "ja") == "聞き耳"
    assert pack.display_name("图书馆", "ja") == "図書館"
    assert pack.display_name("克苏鲁神话", "ja") == "クトゥルフ神話"
    assert pack.rank_label("regular", "ja") == "レギュラー成功"
    assert pack.rank_label("extreme", "ja-JP") == "イクストリーム成功"
    assert pack.rank_label("fumble", "ja") == "ファンブル"
    assert "心理的恐怖" in pack.expertise_text("ja")

    assert pack.commands["クトゥルフ"].action == "make_char"
    assert pack.commands["正気度判定"].tool == "sanity_check"
    assert pack.commands["成長判定"].tool == "skill_growth"
    assert pack.commands["幸運消費"].tool == "spend_luck"
    assert pack.commands["不定の狂気"].args == {"table": "indefinite"}


def test_coc7_japanese_madness_tables_are_japanese():
    pack = load_rulepack("coc7-ja")
    madness = pack.subsystems["random_madness"]

    assert madness.label("ja-JP") == "狂気症状"
    temporary = madness.table("一時的")
    long_term = madness.table("長期")
    indefinite = madness.table("不定")

    assert temporary is not None
    assert long_term is not None
    assert indefinite is not None
    assert temporary.display["ja"] == "一時的狂気"
    assert long_term.display["ja"] == "長期の狂気"
    assert indefinite.display["ja"] == "不定の狂気"
    assert temporary.entries[0].startswith("記憶喪失：")
    assert long_term.entries[0].startswith("恐怖症：")
    assert indefinite.entries[0].startswith("周囲のすべてが")
