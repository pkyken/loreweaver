from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "rulepacks" / "coc7.yaml"
TEST = ROOT / "tests" / "i18n" / "test_coc7_japanese.py"

ALIASES: dict[str, list[str]] = {
    "力量": ["筋力"],
    "体质": ["体質"],
    "智力": ["知性", "アイデア"],
    "意志": ["精神力"],
    "教育": ["教育値", "知識"],
    "幸运": ["幸運"],
    "DB": ["ダメージ・ボーナス", "ダメージボーナス"],
    "体格": ["ビルド"],
    "移动力": ["移動率"],
    "护甲": ["装甲"],
    "理智": ["正気度"],
    "理智上限": ["正気度上限"],
    "生命值": ["耐久力", "ヒット・ポイント"],
    "生命值上限": ["耐久力上限"],
    "魔法值": ["マジック・ポイント"],
    "魔法值上限": ["マジック・ポイント上限"],
    "信用评级": ["信用"],
    "取悦": ["魅惑"],
    "话术": ["言いくるめ"],
    "恐吓": ["威圧"],
    "说服": ["説得"],
    "母语": ["母国語"],
    "外语": ["ほかの言語", "外国語"],
    "估价": ["鑑定"],
    "乔装": ["変装"],
    "潜行": ["隠密"],
    "追踪": ["追跡"],
    "侦查": ["目星"],
    "聆听": ["聞き耳"],
    "读唇": ["読唇術"],
    "图书馆": ["図書館"],
    "生存": ["サバイバル"],
    "攀爬": ["登攀"],
    "跳跃": ["跳躍"],
    "骑乘": ["乗馬"],
    "游泳": ["水泳"],
    "潜水": ["ダイビング"],
    "艺术与手艺": ["芸術／製作", "芸術/製作"],
    "表演": ["演技"],
    "美术": ["美術"],
    "伪造": ["偽造"],
    "摄影": ["写真術"],
    "写作": ["文芸"],
    "音乐": ["音楽"],
    "舞蹈": ["ダンス"],
    "厨艺": ["料理"],
    "妙手": ["手さばき"],
    "锁匠": ["鍵開け"],
    "电气维修": ["電気修理"],
    "机械维修": ["機械修理"],
    "计算机使用": ["コンピューター", "コンピュータ"],
    "导航": ["ナビゲート"],
    "汽车驾驶": ["運転（自動車）", "運転(自動車)"],
    "驾驶:飞行器": ["操縦（航空機）", "操縦(航空機)"],
    "驾驶:船": ["操縦（船舶）", "操縦(船舶)"],
    "驯兽": ["動物使い"],
    "操作重型机械": ["重機械操作"],
    "斗殴": ["近接戦闘（格闘）", "近接戦闘(格闘)"],
    "斧": ["近接戦闘（斧）", "近接戦闘(斧)"],
    "链锯": ["近接戦闘（チェーンソー）", "近接戦闘(チェーンソー)"],
    "连枷": ["近接戦闘（フレイル）", "近接戦闘(フレイル)"],
    "绞索": ["近接戦闘（絞殺ひも）", "近接戦闘(絞殺ひも)"],
    "矛": ["近接戦闘（槍）", "近接戦闘(槍)"],
    "剑": ["近接戦闘（刀剣）", "近接戦闘(刀剣)"],
    "鞭": ["近接戦闘（むち）", "近接戦闘(むち)"],
    "射击": ["射撃"],
    "手枪": ["射撃（拳銃）", "射撃(拳銃)"],
    "步霰": ["射撃（ライフル／ショットガン）", "射撃(ライフル/ショットガン)"],
    "投掷": ["投擲"],
    "炮术": ["砲", "砲術"],
    "急救": ["応急手当"],
    "催眠": ["催眠術"],
    "会计": ["経理"],
    "历史": ["歴史"],
    "博物": ["博物学"],
    "人类学": ["人類学"],
    "神秘学": ["オカルト"],
    "电子学": ["電子工学"],
    "天文学": ["科学（天文学）", "科学(天文学)"],
    "生物学": ["科学（生物学）", "科学(生物学)"],
    "植物学": ["科学（植物学）", "科学(植物学)"],
    "化学": ["科学（化学）", "科学(化学)"],
    "密码学": ["科学（暗号学）", "科学(暗号学)"],
    "工程学": ["科学（工学）", "科学(工学)"],
    "司法科学": ["科学（法医学）", "科学(法医学)"],
    "地质学": ["科学（地質学）", "科学(地質学)"],
    "数学": ["科学（数学）", "科学(数学)"],
    "气象学": ["科学（気象学）", "科学(気象学)"],
    "药学": ["科学（薬学）", "科学(薬学)"],
    "物理学": ["科学（物理学）", "科学(物理学)"],
    "动物学": ["科学（動物学）", "科学(動物学)"],
    "克苏鲁神话": ["クトゥルフ神話"],
}

DISPLAY: dict[str, str] = {
    "bonus": "ボーナス・ダイス",
    "penalty": "ペナルティ・ダイス",
    "力量": "STR",
    "体质": "CON",
    "体型": "SIZ",
    "敏捷": "DEX",
    "外貌": "APP",
    "智力": "INT",
    "意志": "POW",
    "教育": "EDU",
    "幸运": "幸運",
    "理智": "正気度",
    "理智上限": "正気度上限",
    "生命值": "耐久力",
    "生命值上限": "耐久力上限",
    "魔法值": "マジック・ポイント",
    "魔法值上限": "マジック・ポイント上限",
    "DB": "ダメージ・ボーナス",
    "体格": "ビルド",
    "移动力": "MOV",
    "护甲": "装甲",
    "闪避": "回避",
    "灵感": "アイデア",
    "知识": "知識",
    "信用评级": "信用",
    "取悦": "魅惑",
    "话术": "言いくるめ",
    "恐吓": "威圧",
    "说服": "説得",
    "心理学": "心理学",
    "母语": "母国語",
    "外语": "ほかの言語",
    "估价": "鑑定",
    "乔装": "変装",
    "潜行": "隠密",
    "追踪": "追跡",
    "侦查": "目星",
    "聆听": "聞き耳",
    "读唇": "読唇術",
    "图书馆": "図書館",
    "生存": "サバイバル",
    "攀爬": "登攀",
    "跳跃": "跳躍",
    "骑乘": "乗馬",
    "游泳": "水泳",
    "潜水": "ダイビング",
    "艺术与手艺": "芸術／製作",
    "表演": "演技",
    "美术": "美術",
    "伪造": "偽造",
    "摄影": "写真術",
    "写作": "文芸",
    "音乐": "音楽",
    "舞蹈": "ダンス",
    "厨艺": "料理",
    "妙手": "手さばき",
    "锁匠": "鍵開け",
    "电气维修": "電気修理",
    "机械维修": "機械修理",
    "计算机使用": "コンピューター",
    "导航": "ナビゲート",
    "汽车驾驶": "運転（自動車）",
    "驾驶:飞行器": "操縦（航空機）",
    "驾驶:船": "操縦（船舶）",
    "驯兽": "動物使い",
    "操作重型机械": "重機械操作",
    "斗殴": "近接戦闘（格闘）",
    "斧": "近接戦闘（斧）",
    "链锯": "近接戦闘（チェーンソー）",
    "连枷": "近接戦闘（フレイル）",
    "绞索": "近接戦闘（絞殺ひも）",
    "矛": "近接戦闘（槍）",
    "剑": "近接戦闘（刀剣）",
    "鞭": "近接戦闘（むち）",
    "射击": "射撃",
    "手枪": "射撃（拳銃）",
    "步霰": "射撃（ライフル／ショットガン）",
    "投掷": "投擲",
    "爆破": "爆破",
    "炮术": "砲",
    "急救": "応急手当",
    "医学": "医学",
    "精神分析": "精神分析",
    "催眠": "催眠術",
    "会计": "経理",
    "法律": "法律",
    "历史": "歴史",
    "考古学": "考古学",
    "博物": "博物学",
    "人类学": "人類学",
    "神秘学": "オカルト",
    "电子学": "電子工学",
    "科学": "科学",
    "天文学": "科学（天文学）",
    "生物学": "科学（生物学）",
    "植物学": "科学（植物学）",
    "化学": "科学（化学）",
    "密码学": "科学（暗号学）",
    "工程学": "科学（工学）",
    "司法科学": "科学（法医学）",
    "地质学": "科学（地質学）",
    "数学": "科学（数学）",
    "气象学": "科学（気象学）",
    "药学": "科学（薬学）",
    "物理学": "科学（物理学）",
    "动物学": "科学（動物学）",
    "克苏鲁神话": "クトゥルフ神話",
    "职业": "職業",
    "年龄": "年齢",
}


def add_aliases(text: str) -> str:
    start = text.index("alias:\n")
    end = text.index("st_show:\n", start)
    lines = text[start:end].splitlines(keepends=True)
    found: set[str] = set()
    for index, line in enumerate(lines):
        for canonical, aliases in ALIASES.items():
            prefix = f"  {canonical}: ["
            if not line.startswith(prefix):
                continue
            found.add(canonical)
            newline = "\n" if line.endswith("\n") else ""
            body = line[len(prefix) : -len(newline)]
            if not body.endswith("]"):
                raise RuntimeError(f"malformed alias line: {canonical}")
            body = body[:-1]
            for alias in aliases:
                if alias not in body:
                    body += ", " + json.dumps(alias, ensure_ascii=False)
            lines[index] = prefix + body + "]" + newline
            break
    missing = set(ALIASES) - found
    if missing:
        raise RuntimeError(f"alias lines not found: {sorted(missing)}")
    if not any(line.startswith("  闪避:") for line in lines):
        lines.append('  闪避: [dodge, Dodge, "回避"]\n')
    return text[:start] + "".join(lines) + text[end:]


def replace_once(text: str, old: str, new: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"anchor not found: {old}")
    return text.replace(old, new, 1)


def main() -> None:
    text = PACK.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'names: [coc, coc7, "call of cthulhu"]',
        'names: [coc, coc7, "call of cthulhu", "クトゥルフ神話TRPG", "新クトゥルフ神話TRPG"]',
    )
    text = add_aliases(text)

    for old, new in {
        "regular: {prefixes: {en: [regular], zh: []}}":
            "regular: {prefixes: {en: [regular], zh: [], ja: [レギュラー]}}",
        'hard: {target: "floor(target / 2)", prefixes: {en: [hard], zh: [困难]}}':
            'hard: {target: "floor(target / 2)", prefixes: {en: [hard], zh: [困难], ja: [ハード]}}',
        'extreme: {target: "floor(target / 5)", prefixes: {en: [extreme], zh: [极难]}}':
            'extreme: {target: "floor(target / 5)", prefixes: {en: [extreme], zh: [极难], ja: [イクストリーム, エクストリーム]}}',
        'critical: {target: "1", prefixes: {en: [critical], zh: [大成功]}}':
            'critical: {target: "1", prefixes: {en: [critical], zh: [大成功], ja: [クリティカル]}}',
        "display: {en: Sanity, zh: 理智}": "display: {en: Sanity, zh: 理智, ja: 正気度}",
        "display: {en: Skill growth, zh: 技能成长}": "display: {en: Skill growth, zh: 技能成长, ja: 技能成長}",
        "display: {en: Luck, zh: 幸运}": "display: {en: Luck, zh: 幸运, ja: 幸運}",
        "display: {en: Opposed check, zh: 对抗检定}": "display: {en: Opposed check, zh: 对抗检定, ja: 対抗判定}",
        "display: {en: Madness symptom, zh: 疯狂症状}": "display: {en: Madness symptom, zh: 疯狂症状, ja: 狂気の症状}",
        "display: {en: Temporary madness, zh: 临时性疯狂}": "display: {en: Temporary madness, zh: 临时性疯狂, ja: 一時的狂気}",
        "aliases: [临时, temporary]": "aliases: [临时, temporary, 一時的, 一時]",
        "display: {en: Long-term madness, zh: 总结性疯狂}": "display: {en: Long-term madness, zh: 总结性疯狂, ja: 長期の狂気}",
        "aliases: [总结, 总结性]": "aliases: [总结, 总结性, 長期, 長期の狂気]",
        "display: {en: Indefinite madness, zh: 不定性疯狂}": "display: {en: Indefinite madness, zh: 不定性疯狂, ja: 不定の狂気}",
        "aliases: [不定, 不定性]": "aliases: [不定, 不定性, 不定の狂気]",
    }.items():
        text = replace_once(text, old, new)

    labels_anchor = (
        "  zh:\n"
        "    crit: [大成功]\n"
        "    extreme: [极难成功]\n"
        "    hard: [困难成功]\n"
        "    regular: {display: 成功, markers: [常规成功, 普通成功]}\n"
        "    fail: {display: 失败, markers: []}\n"
        "    fumble: [大失败]\n"
    )
    labels_ja = (
        "  ja:\n"
        "    crit: [クリティカル成功]\n"
        "    extreme: [イクストリーム成功]\n"
        "    hard: [ハード成功]\n"
        "    regular: {display: レギュラー成功, markers: [レギュラー成功]}\n"
        "    fail: {display: 失敗, markers: []}\n"
        "    fumble: [ファンブル, 致命的失敗]\n"
    )
    if labels_ja not in text:
        if labels_anchor not in text:
            raise RuntimeError("labels anchor not found")
        text = text.replace(labels_anchor, labels_anchor + labels_ja, 1)

    if "\n  ja:\n    bonus: ボーナス・ダイス\n" not in text:
        display_block = "  ja:\n" + "\n".join(
            f"    {key}: {value}" for key, value in DISPLAY.items()
        ) + "\n"
        text = text.replace("display:\n", "display:\n" + display_block, 1)

    expertise_ja = (
        '  ja: "# 新クトゥルフ神話TRPG（CoC7）— キーパー\\n'
        '流血表現より心理的恐怖を重視し、真相は段階的に明かしてください。本当に恐ろしいものへ直面した場面で正気度判定を行い、狂気への下降を演出します。探索がプレイを動かし、成功だけでなく失敗も物語を前へ進めます。成功段階、ボーナス／ペナルティ・ダイス、クリティカルとファンブルはエンジンが計算するため、その結果に従って描写してください。"\n'
    )
    if expertise_ja not in text:
        marker = "\n# Sheet substrate (M16 stage B):"
        if marker not in text:
            raise RuntimeError("expertise insertion anchor not found")
        text = text.replace(marker, expertise_ja + marker, 1)

    PACK.write_text(text, encoding="utf-8")
    TEST.write_text(
        '''from core.rulepacks import load_rulepack\n\n\ndef test_coc7_japanese_vocabulary_and_presentation():\n    pack = load_rulepack("coc7")\n\n    assert pack.resolve_skill("目星") == "侦查"\n    assert pack.resolve_skill("聞き耳") == "聆听"\n    assert pack.resolve_skill("図書館") == "图书馆"\n    assert pack.resolve_skill("正気度") == "理智"\n    assert pack.resolve_skill("応急手当") == "急救"\n    assert pack.resolve_skill("クトゥルフ神話") == "克苏鲁神话"\n\n    assert pack.display_name("侦查", "ja") == "目星"\n    assert pack.display_name("聆听", "ja-JP") == "聞き耳"\n    assert pack.display_name("克苏鲁神话", "ja") == "クトゥルフ神話"\n    assert pack.rank_label("crit", "ja") == "クリティカル成功"\n    assert pack.rank_label("extreme", "ja") == "イクストリーム成功"\n    assert pack.rank_label("hard", "ja") == "ハード成功"\n    assert pack.rank_label("regular", "ja") == "レギュラー成功"\n    assert pack.rank_label("fumble", "ja") == "ファンブル"\n\n    difficulty_prefixes = {\n        difficulty.id: tuple(difficulty.prefixes.get("ja", ()))\n        for difficulty in pack.resolver.difficulties\n    }\n    assert difficulty_prefixes["regular"] == ("レギュラー",)\n    assert difficulty_prefixes["hard"] == ("ハード",)\n    assert difficulty_prefixes["extreme"] == ("イクストリーム", "エクストリーム")\n    assert difficulty_prefixes["critical"] == ("クリティカル",)\n\n\ndef test_coc7_existing_english_and_chinese_vocabulary_stays_compatible():\n    pack = load_rulepack("coc7")\n\n    assert pack.resolve_skill("spot hidden") == "侦查"\n    assert pack.resolve_skill("侦察") == "侦查"\n    assert pack.display_name("侦查", "en") == "Spot Hidden"\n    assert pack.rank_label("hard", "zh") == "困难成功"\n''',
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
