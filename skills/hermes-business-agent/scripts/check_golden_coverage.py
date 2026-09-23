#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_golden_coverage.py — Golden 用例集与契约表的对账门禁（离线、无需 Key、不执行用例）。

主线位置：SKILL.md 第 ⑤ 步（每加一个工具跑一次，作为逐工具的第一道门）与第 ⑦ 步
（跑 Golden 回归之前先对账）。它不判断回答对不对——那由用例里的断言在第 ⑦ 步执行时判断；
本脚本只回答一件事：**契约表承诺的覆盖，用例集里究竟有没有兑现**。

为什么需要它：第 ① 步的验收表、第 ⑤ 步落码的面表、第 ⑦ 步用的用例集是三份各自演进的产物。
「每条用例都能回指验收表某一行」「每个工具都有回归覆盖」这两条判据此前只能靠人工点数核对，
点数这一步一旦省掉，缺的那一格没人发现就带进第 ⑧ 步。

十二条硬门禁（任一 FAIL 则退出码 1）：
  [1]  golden_loaded            —— 每个 --golden 文件读得出静态用例列表，每条用例有 id 且全局唯一
  [2]  contract_tables          —— 契约表文件里按表头找得到面表与验收表（列名见 `19` §7 第 1、7 张）
  [3]  acceptance_signoff       —— 验收表每行的「确认人」「确认日期」两格都非空
  [4]  case_anchored            —— 每条用例的 id 出现在验收表某行的「派生的 Golden 用例编号」列
  [5]  ref_planted              —— 验收表列出的每个编号在 Golden 集里存在（写了编号却没落地用例）
  [6]  layer_vocabulary         —— 面表「层」列取值全部落在 只读 / 受控 / 禁止 三档内
  [7]  forbidden_declared_global—— 禁止面行的「场景」列是全场景表述（缺席是全场景成立的前提）
  [8]  forbidden_not_triggered  —— 禁止面工具不出现在任何用例的 behavior 里（只能出现在 forbidden 里）
  [9]  calc_row_has_source     —— 面表「归属」判为计算题的行登记了结果来源（那一格填的应当是快照段名或
                                   handler 名，不是工具名；`19` §7 第 1 张第 2 段）
  [10] tool_covered            —— 面表上只读层与受控层的每个工具，至少被一条用例的 behavior 触发
  [11] write_readback          —— 受控写层每个工具，至少有一条 readback 为真的用例
  [12] no_weak_assertion       —— 每条用例有 prompt，且 fields 或 invariants 非空；
                                   fields 的值不是占位词（「非空」「任意」「包含」这类把值断言降级成存在性的写法）

非阻断提示：某工具的用例数少于 3 条时打印一行提醒（结构基线见 `20` §4.2），不判失败——
一条用例属于正例、负例还是边界，无法从用例字段派生，硬卡会误伤已经写对的用例集。

本脚本查不到的三件事（别把它当回归本身）：
  · 用例是否真的跑过、通过率多少：它不执行用例，执行在第 ⑦ 步。
  · 期望值对不对：值的根据是验收表那一行的业务原话，机检只核「有没有回指」。
  · 正例/负例/边界的配比够不够：理由见上面那条非阻断提示。
  另有一处只核到半程：计算题行填的是「结果来源名」还是「工具名」，机检分不出（两者形状相同），
  所以 [9] 只断言那一格非空，填错内容留给第 ⑦ 步的工具序列断言暴露。

用法：
  python scripts/check_golden_coverage.py --golden tests/golden.py --contract docs/契约表.md
  python scripts/check_golden_coverage.py --golden a.py --golden b.json --var CASES --json

约定：每个 --golden 文件里的用例集必须是一个**静态字面量列表**（默认变量名 GOLDEN，`20` §4.3）。
用循环或推导式生成的用例集本脚本读不出，这是刻意的：机检要求每条用例出生即可指认，
而生成器改一次规则会同时改掉几百条用例的期望值——那正是第 ⑦ 步禁止的「失败就改用例期望去过」的批量形态。

退出码：0 = 十二条全过；1 = 任一条失败或用例集/契约表读不出。
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

# 表格单元格里的多值分隔（顿号、逗号、分号、斜杠、空白）
_SPLIT = re.compile(r"[、,，;；\s/]+")
# 工具名与用例编号的可识别形状
_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.\-]*$")
_SEP_CELL_RE = re.compile(r"^:?-{2,}:?$")
# 编号列里允许出现的「本期还没有编号」写法
_BLANK_TOKENS = {"无", "暂无", "待定", "同上", "-", "—", "–", "n/a", "na", ""}
# 值断言被降级成存在性断言的典型占位词
_PLACEHOLDERS = {"非空", "任意", "包含", "有值", "不为空", "not empty", "any"}
# 全场景表述
_ALL_SCOPE_RE = re.compile(r"全|所有|任意|every|all", re.I)
# 三档之外的层列取值在此判失败；顺序即优先级（先判禁止，再判受控写）
TIERS = (("禁止", "forbidden"), ("受控", "write"), ("写", "write"),
         ("只读", "read"), ("读", "read"))


def _norm(cell: str) -> str:
    return re.sub(r"[*`\u3000]", "", cell).strip()


def _is_sep_row(cells: list[str]) -> bool:
    norm = [_norm(c) for c in cells]
    return any(_SEP_CELL_RE.match(c) for c in norm) and all(
        c == "" or bool(_SEP_CELL_RE.match(c)) for c in norm)


def _markdown_tables(text: str) -> list[list[list[str]]]:
    """扫出 markdown 表格，每张表返回行列表（第 0 行是表头）；至少要有表头加一行内容。"""
    tables: list[list[list[str]]] = []
    buf: list[list[str]] = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("|") and s.endswith("|") and s.count("|") >= 2:
            cells = [c.strip() for c in s.strip("|").split("|")]
            if buf and _is_sep_row(cells):
                continue
            buf.append(cells)
        else:
            if len(buf) >= 2:
                tables.append(buf)
            buf = []
    if len(buf) >= 2:
        tables.append(buf)
    return tables


def _find_table(tables, *header_keys: str):
    for t in tables:
        head = " ".join(_norm(c) for c in t[0])
        if all(k in head for k in header_keys):
            return t
    return None


def _col_index(table, *keys: str):
    for i, c in enumerate(table[0]):
        n = _norm(c)
        if any(k in n for k in keys):
            return i
    return None


def _cell(row: list[str], idx) -> str:
    if idx is None or idx >= len(row):
        return ""
    return _norm(row[idx])


def _name_tokens(cell: str) -> list[str]:
    out = []
    for raw in _SPLIT.split(re.sub(r"[（(].*?[)）]", "", cell)):
        tok = raw.strip().strip("。；;，,")
        if tok and _NAME_RE.match(tok):
            out.append(tok)
    return out


def _tier(layer_cell: str) -> str:
    for key, tier in TIERS:
        if key in layer_cell:
            return tier
    return "unknown"


def _load_cases(path: Path, var: str) -> tuple[list | None, str]:
    if not path.is_file():
        return None, f"文件不存在：{path}"
    text = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(text)
        except Exception as exc:  # noqa: BLE001 —— 报错原文比类型重要
            return None, f"JSON 解析失败：{exc}"
        if isinstance(data, list):
            return data, ""
        if isinstance(data, dict) and isinstance(data.get(var), list):
            return data[var], ""
        return None, f"JSON 根节点既不是数组也不是 {{{var!r}: [...]}} 形态"
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return None, f"语法错误：{exc}"
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
        else:
            continue
        for tgt in targets:
            if isinstance(tgt, ast.Name) and tgt.id == var:
                try:
                    value = ast.literal_eval(node.value)
                except Exception as exc:  # noqa: BLE001
                    return None, (f"{var} 不是静态字面量（{type(exc).__name__}）"
                                  "——用例集必须是字面量列表，理由见本文件开头的约定")
                if not isinstance(value, list):
                    return None, f"{var} 不是列表字面量"
                return value, ""
    return None, f"未找到模块级 {var} 赋值"


class Recon:
    """一次对账：跑十二条门禁，攒结果，最后统一输出。"""

    def __init__(self) -> None:
        self.checks: list[tuple[str, str, str, str]] = []
        self.notes: list[str] = []

    def add(self, cid: str, desc: str, ok: bool, detail: str = "") -> None:
        self.checks.append((cid, desc, "PASS" if ok else "FAIL", detail or ("OK" if ok else "无明细")))

    @property
    def failed(self) -> list[str]:
        return [c[0] for c in self.checks if c[2] == "FAIL"]


def run(golden_paths: list[Path], contract_path: Path, var: str) -> Recon:
    r = Recon()

    # [1] 用例集读得出、id 齐备且唯一
    cases: list[dict] = []
    read_errs: list[str] = []
    for p in golden_paths:
        got, err = _load_cases(p, var)
        if got is None:
            read_errs.append(f"{p}: {err}")
            continue
        cases.extend(got)
    bad_type = sum(1 for c in cases if not isinstance(c, dict))
    cases = [c for c in cases if isinstance(c, dict)]
    ids = [str(c.get("id") or "").strip() for c in cases]
    no_id = sum(1 for i in ids if not i or i == "None")
    dup = sorted({i for i in ids if i and i != "None" and ids.count(i) > 1})
    ok1 = not read_errs and bool(cases) and not no_id and not dup and not bad_type
    detail1 = "；".join(read_errs) if read_errs else (
        f"{len(cases)} 条用例"
        + (f"，{bad_type} 条不是对象（列表项必须是键值对象，不做静默丢弃）" if bad_type else "")
        + (f"，{no_id} 条缺 id" if no_id else "")
        + (f"，重复 id：{'、'.join(dup[:5])}" if dup else ""))
    r.add("golden_loaded", "用例集读得出，且每条用例有唯一 id", ok1, detail1)

    # [2] 两张契约表按表头找得到
    surface = acceptance = None
    if not contract_path.is_file():
        r.add("contract_tables", "契约表文件里找得到面表与验收表", False, f"文件不存在：{contract_path}")
    else:
        tables = _markdown_tables(contract_path.read_text(encoding="utf-8", errors="replace"))
        surface = _find_table(tables, "工具", "审批")
        acceptance = _find_table(tables, "怎么算做对了")
        miss = []
        if surface is None:
            miss.append("面表（表头需含「工具」「审批要求」两列）")
        if acceptance is None:
            miss.append("验收表（表头需含「怎么算做对了」列）")
        r.add("contract_tables", "契约表文件里找得到面表与验收表", not miss,
              "、".join(miss) if miss else f"用例表列数 {len(surface[0])}，验收表列数 {len(acceptance[0])}")

    # [3] 验收表逐行有背书
    listed_ids: list[str] = []
    junk_ids: list[str] = []
    if acceptance is None:
        r.add("acceptance_signoff", "验收表每行的确认人与确认日期非空", False, "验收表未找到，无法核查")
    else:
        c_conf = _col_index(acceptance, "确认人")
        c_date = _col_index(acceptance, "确认日期", "确认时间")
        c_ids = _col_index(acceptance, "用例编号", "Golden")
        c_goal = _col_index(acceptance, "本期目标")
        missing_cols = [n for n, i in (("确认人", c_conf), ("确认日期", c_date),
                                       ("派生的 Golden 用例编号", c_ids)) if i is None]
        if missing_cols:
            r.add("acceptance_signoff", "验收表每行的确认人与确认日期非空", False,
                  f"缺列：{'、'.join(missing_cols)}")
        else:
            unsigned, numbered = [], 0
            for row in acceptance[1:]:
                goal = _cell(row, c_goal) or f"第 {numbered + 2} 行"
                numbered += 1
                if not _cell(row, c_conf) or not _cell(row, c_date):
                    unsigned.append(goal[:24])
                cell = _cell(row, c_ids)
                for tok in _SPLIT.split(re.sub(r"[（(].*?[)）]", "", cell)):
                    tok = tok.strip().strip("。；;，,")
                    if tok.lower() in _BLANK_TOKENS:
                        continue
                    if _NAME_RE.match(tok):
                        listed_ids.append(tok)
                    else:
                        junk_ids.append(f"{goal[:16]}→{tok}")
            r.add("acceptance_signoff", "验收表每行的确认人与确认日期非空", not unsigned,
                  f"{numbered} 行中 {len(unsigned)} 行缺背书：" + "、".join(unsigned[:5])
                  if unsigned else f"{numbered} 行全部有确认人与确认日期")

    case_ids = {i for i in ids if i and i != "None"}

    # [4] 用例回指验收表 + [5] 验收表编号已落地
    if acceptance is None:
        r.add("case_anchored", "每条用例的 id 出现在验收表的用例编号列", False, "验收表未找到，无法核查")
        r.add("ref_planted", "验收表列出的每个编号都有对应用例", False, "验收表未找到，无法核查")
    else:
        orphan = sorted(case_ids - set(listed_ids))
        r.add("case_anchored", "每条用例的 id 出现在验收表的用例编号列", not orphan,
              f"{len(orphan)} 条用例回指不到验收表（开发自己出的题）：" + "、".join(orphan[:8])
              if orphan else f"{len(case_ids)} 条用例全部能回指到验收表某一行")
        missing_case = sorted(set(listed_ids) - case_ids)
        junk = [] if not junk_ids else [f"{a}（不是可识别的编号形状）" for a in junk_ids[:8]]
        r.add("ref_planted", "验收表列出的每个编号都有对应用例", not missing_case and not junk,
              "；".join(filter(None, [
                  "验收表列了但用例集里没有：" + "、".join(missing_case[:8]) if missing_case else "",
                  "编号列出现无法识别的文本：" + "、".join(junk) if junk else ""])))

    if surface is None:
        for cid, desc in (("layer_vocabulary", "面表「层」列取值全部落在三档内"),
                          ("forbidden_declared_global", "禁止面按全场景登记"),
                          ("forbidden_not_triggered", "禁止面工具未被任何用例期望触发"),
                          ("calc_row_has_source", "归属为计算题的行登记了结果来源"),
                          ("tool_covered", "只读层与受控层的每个工具都有用例触发"),
                          ("write_readback", "受控写层每个工具都有回读用例")):
            r.add(cid, desc, False, "面表未找到，无法核查")
        cases_by_behavior = {}
    else:
        c_tool = _col_index(surface, "工具")
        c_layer = _col_index(surface, "层")
        c_belong = _col_index(surface, "归属")
        c_scene = _col_index(surface, "场景")
        cases_by_behavior = {str(t) for c in cases for t in (c.get("behavior") or [])}
        cases_by_forbidden = {str(t) for c in cases for t in (c.get("forbidden") or [])}

        tiers: dict[str, str] = {}
        unknown_layer, forbidden_scenes, calc_no_source = [], [], []
        for row in surface[1:]:
            tools = _name_tokens(_cell(row, c_tool))
            tier = _tier(_cell(row, c_layer))
            scene = _cell(row, c_scene)
            belong = _cell(row, c_belong)
            if "计算" in belong:
                source = _cell(row, c_tool)
                if not source or source.lower() in _BLANK_TOKENS:
                    calc_no_source.append(scene or "场景未填")
                continue
            if not tools:
                continue
            if tier == "unknown":
                unknown_layer.append(f"{'、'.join(tools)}→「{_cell(row, c_layer) or '空'}」")
                continue
            for t in tools:
                if t in tiers and tiers[t] != tier:
                    unknown_layer.append(f"{t} 同时登记为 {tiers[t]} 与 {tier}")
                tiers[t] = tier
            if tier == "forbidden" and scene and not _ALL_SCOPE_RE.search(scene):
                forbidden_scenes.append(f"{'、'.join(tools)}→场景「{scene}」")

        r.add("layer_vocabulary", "面表「层」列取值全部落在三档内", not unknown_layer,
              "无法归类的层取值：" + "；".join(unknown_layer[:6]) if unknown_layer
              else f"共 {len(tiers)} 个工具已归类（只读/受控写/禁止）")
        r.add("forbidden_declared_global", "禁止面按全场景登记（缺席对所有入口成立）",
              not forbidden_scenes,
              "禁止面被写成分场景行：" + "；".join(forbidden_scenes[:6]) if forbidden_scenes else "OK")
        leaked = sorted({t for t, tier in tiers.items() if tier == "forbidden"} & cases_by_behavior)
        r.add("forbidden_not_triggered", "禁止面工具未被任何用例期望触发", not leaked,
              "禁止面出现在用例的 behavior 里：" + "、".join(leaked[:8]) if leaked else "OK")
        r.add("calc_row_has_source", "归属为计算题的行登记了结果来源", not calc_no_source,
              "计算题格空着（结果从哪来没登记）：" + "；".join(calc_no_source[:6]) if calc_no_source else "OK")

        covered = {t for t, tier in tiers.items() if tier in ("read", "write")}
        uncovered = sorted(covered - cases_by_behavior)
        r.add("tool_covered", "只读层与受控层的每个工具都有用例触发", not uncovered,
              f"{len(uncovered)} 个工具无回归覆盖：" + "、".join(uncovered[:8]) if uncovered
              else f"{len(covered)} 个在面工具全部有用例")
        write_tools = {t for t, tier in tiers.items() if tier == "write"}
        readback_tools = {str(t) for c in cases if c.get("readback")
                          for t in (c.get("behavior") or [])}
        no_readback = sorted(write_tools - readback_tools)
        r.add("write_readback", "受控写层每个工具都有 readback 为真的用例", not no_readback,
              "写面工具缺回读用例：" + "、".join(no_readback[:8]) if no_readback
              else f"{len(write_tools)} 个写工具均有回读用例")

        for t in sorted(covered):
            n = sum(1 for c in cases if t in {str(x) for x in (c.get("behavior") or [])})
            if n < 3:
                r.notes.append(f"{t}：用例 {n} 条（`20` §4.2 结构基线要 3 正 2 负 2 边，"
                               "正负边不可从用例派生，故只提示不阻断）")
            if t in cases_by_forbidden and t not in cases_by_behavior:
                r.notes.append(f"{t}：只出现在 forbidden 里，没有正路径用例")

    # [12] 断言强度
    weak = []
    for c in cases:
        cid = str(c.get("id") or "(缺 id)")
        fields = c.get("fields")
        invariants = c.get("invariants")
        has_assert = (isinstance(fields, dict) and fields) or (isinstance(invariants, list) and invariants)
        bad = []
        if isinstance(fields, dict):
            for k, v in fields.items():
                if isinstance(v, str) and v.strip().lower() in _PLACEHOLDERS:
                    bad.append(f"{k}={v}")
        if not str(c.get("prompt") or "").strip():
            bad.append("缺 prompt")
        if not has_assert or bad:
            weak.append(f"{cid}：" + ("无用值断言" if not has_assert else "") +
                        ("；".join(bad) if bad else ""))
    r.add("no_weak_assertion", "每条用例有值断言或不变量断言，且值断言未降级成占位词", not weak,
          f"{len(weak)} 条弱断言：" + "；".join(weak[:6]) if weak
          else (f"{len(cases)} 条全部有断言" if cases else "用例集为空，本条无对象可核（失败原因见 golden_loaded）"))
    return r


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Golden 用例集与契约表对账门禁")
    p.add_argument("--golden", action="append", default=[],
                   help="用例集文件（.py 或 .json），可重复传多个")
    p.add_argument("--contract", required=True, help="契约表所在的 markdown 文件（含面表与验收表）")
    p.add_argument("--var", default="GOLDEN", help="用例集变量名（默认 GOLDEN）")
    p.add_argument("--json", action="store_true", help="输出 JSON，供 CI 汇总")
    args = p.parse_args(argv)

    if not args.golden:
        print("错误：至少要传一个 --golden 用例集文件。", file=sys.stderr)
        return 1

    r = run([Path(g) for g in args.golden], Path(args.contract), args.var)
    ok = not r.failed

    if args.json:
        print(json.dumps({"ok": ok, "failed": r.failed, "notes": r.notes,
                          "checks": [{"id": c[0], "desc": c[1], "status": c[2], "detail": c[3]}
                                     for c in r.checks]}, ensure_ascii=False, indent=2))
        return 0 if ok else 1

    print(f"用例 ↔ 契约对账（用例集：{'、'.join(args.golden)}｜契约表：{args.contract}）")
    print("=" * 68)
    for cid, desc, status, detail in r.checks:
        print(f"[{status}] {cid} — {desc}")
        print(f"       {detail}")
    print("-" * 68)
    if r.notes:
        print("提示（不阻断）：")
        for n in r.notes:
            print(f"  · {n}")
    print("=" * 68)
    if ok:
        print("对账通过：十二条硬门禁全绿。用例覆盖与契约表一致，可进第 ⑦ 步跑回归。")
    else:
        print(f"对账未通过：{len(r.failed)} 条硬门禁失败（{'、'.join(r.failed)}）。"
              "回第 ① 步补契约行或回第 ⑤ 步补用例，禁止改用例编号迁就用例集。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
