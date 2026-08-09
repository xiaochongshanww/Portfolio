from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from src.app.core.config import settings
from src.app.rag.citations import validate_trace_citations
from src.pipeline.active_db import read_active_manifest
from src.pipeline.audit.multimodal import find_source_pdf
from src.pipeline.paths import RAW_DIR

ANSWER_EVAL_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "evaluation" / "answer_holdout.jsonl"
)
ANSWER_CASE_TYPES = {"direct_value", "formula", "boundary", "false_premise", "no_evidence"}
REFUSAL_TERMS = (
    "当前材料中未找到明确依据",
    "无法可靠回答",
    "未检索到足够",
    "未找到",
    "不存在",
    "没有直接规定",
)
IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
SYMBOLIC_TERM_PATTERN = re.compile(r"[\\_{}α-ωΑ-Ω]")
LATEX_FORMAT_COMMAND_PATTERN = re.compile(r"\\(?:mathrm|mathbf|text|operatorname|rm|tt)")
GREEK_SYMBOL_NAMES = {
    "α": "alpha",
    "β": "beta",
    "γ": "gamma",
    "δ": "delta",
    "μ": "mu",
    "σ": "sigma",
    "φ": "phi",
    "ψ": "psi",
    "ω": "omega",
}


@dataclass(frozen=True)
class AnswerEvaluationCase:
    id: str
    query: str
    type: str
    expected_all: list[str]
    expected_any_groups: list[list[str]]
    forbidden_terms: list[str]
    expected_citations: list[str]
    expected_unit_groups: list[list[str]]
    requires_refusal: bool = False
    requires_image: bool = True


def validate_answer_cases(
    cases: list[AnswerEvaluationCase],
    *,
    minimum_count: int = 0,
) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for index, case in enumerate(cases, start=1):
        label = case.id or f"line-{index}"
        if not case.id:
            errors.append(f"{label}: id 不能为空")
        elif case.id in seen:
            errors.append(f"{label}: id 重复")
        seen.add(case.id)
        if not case.query.strip():
            errors.append(f"{label}: query 不能为空")
        if case.type not in ANSWER_CASE_TYPES:
            errors.append(f"{label}: 未知 type={case.type}")
        if not (
            case.expected_all
            or case.expected_any_groups
            or case.expected_citations
            or case.expected_unit_groups
            or case.requires_refusal
        ):
            errors.append(f"{label}: 至少需要一个回答断言")
        if case.requires_refusal and case.type != "no_evidence":
            errors.append(f"{label}: requires_refusal 仅用于 no_evidence")
        if any(not group for group in case.expected_any_groups + case.expected_unit_groups):
            errors.append(f"{label}: 任选匹配组不能为空")
    if len(cases) < minimum_count:
        errors.append(f"回答评估集用例数不足：实际 {len(cases)}，最低 {minimum_count}")
    return errors


def load_answer_cases(path: Path = ANSWER_EVAL_PATH) -> list[AnswerEvaluationCase]:
    cases: list[AnswerEvaluationCase] = []
    if not path.exists():
        return cases
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        cases.append(
            AnswerEvaluationCase(
                id=str(data["id"]),
                query=str(data["query"]),
                type=str(data["type"]),
                expected_all=[str(value) for value in data.get("expected_all", [])],
                expected_any_groups=[
                    [str(value) for value in group] for group in data.get("expected_any_groups", [])
                ],
                forbidden_terms=[str(value) for value in data.get("forbidden_terms", [])],
                expected_citations=[str(value) for value in data.get("expected_citations", [])],
                expected_unit_groups=[
                    [str(value) for value in group]
                    for group in data.get("expected_unit_groups", [])
                ],
                requires_refusal=bool(data.get("requires_refusal", False)),
                requires_image=bool(data.get("requires_image", True)),
            )
        )
    errors = validate_answer_cases(
        cases,
        minimum_count=24 if path.resolve() == ANSWER_EVAL_PATH.resolve() else 0,
    )
    if errors:
        raise ValueError("回答评估集契约校验失败：\n- " + "\n- ".join(errors))
    return cases


def extract_markdown_images(answer: str) -> list[dict[str, str]]:
    return [
        {"alt": match.group(1), "url": match.group(2)} for match in IMAGE_PATTERN.finditer(answer)
    ]


def validate_image_reference(url: str) -> tuple[bool, str]:
    parsed = urlparse(url)
    path = unquote(parsed.path)
    page_match = re.fullmatch(r"/page-images/(.+)/(\d+)", path)
    if page_match:
        source, page_text = page_match.groups()
        pdf_path = find_source_pdf(source, RAW_DIR)
        if not pdf_path:
            return False, f"页面截图源 PDF 不存在: {source}"
        try:
            import fitz

            with fitz.open(pdf_path) as document:
                if int(page_text) < 1 or int(page_text) > len(document):
                    return False, f"页面超出 PDF 范围: {source} page {page_text}"
        except Exception as exc:
            return False, f"无法读取页面截图源 PDF: {exc}"
        return True, ""
    if path.startswith("/images/"):
        filename = unquote(path.removeprefix("/images/"))
        image_path = (settings.img_dir / filename).resolve()
        image_root = settings.img_dir.resolve()
        if image_path != image_root and image_root not in image_path.parents:
            return False, f"图片路径越界: {url}"
        if not image_path.is_file():
            return False, f"图片文件不存在: {filename}"
        return True, ""
    return False, f"不支持的图片路由: {url}"


def _contains_term(answer: str, term: str) -> bool:
    if "kN/m" in term:

        def normalize_unit(value: str) -> str:
            normalized = value.replace("\\text", "").replace("\\mathrm", "")
            normalized = normalized.replace("{", "").replace("}", "").replace(" ", "")
            normalized = normalized.replace("²", "^2")
            return normalized.lower()

        return "kn/m^2" in normalize_unit(answer)
    if re.fullmatch(r"-?\d+(?:\.\d+)?", term):
        expected = float(term)
        return any(
            abs(float(value) - expected) < 1e-9
            for value in re.findall(r"(?<![\d.])-?\d+(?:\.\d+)?(?![\d.])", answer)
        )
    if SYMBOLIC_TERM_PATTERN.search(term):

        def normalize_symbolic(value: str) -> str:
            normalized = LATEX_FORMAT_COMMAND_PATTERN.sub("", value)
            for symbol, name in GREEK_SYMBOL_NAMES.items():
                normalized = normalized.replace(symbol, name)
            normalized = normalized.replace("\\", "")
            return re.sub(r"[\s{}]", "", normalized).lower()

        return normalize_symbolic(term) in normalize_symbolic(answer)
    return term in answer


def probe_image_url(
    url: str,
    api_base: str,
    *,
    cache: dict[str, tuple[bool, str]] | None = None,
) -> tuple[bool, str]:
    cache = cache if cache is not None else {}
    if url in cache:
        return cache[url]
    import httpx

    parsed = urlparse(url)
    target = f"{api_base.rstrip('/')}{parsed.path}"
    if parsed.query:
        target += f"?{parsed.query}"
    try:
        response = httpx.get(target, timeout=60)
        content_type = response.headers.get("content-type", "")
        result = (
            response.status_code == 200
            and content_type.startswith("image/")
            and len(response.content) > 100,
            "" if response.status_code == 200 else f"HTTP {response.status_code}",
        )
    except Exception as exc:
        result = (False, str(exc))
    cache[url] = result
    return result


def evaluate_answer(
    case: AnswerEvaluationCase,
    answer: str,
    *,
    trace: dict[str, Any] | None = None,
    image_probe: Any = None,
) -> dict[str, Any]:
    checks: dict[str, bool] = {
        "format": all(section in answer for section in ("【结论】", "【依据】", "【说明】")),
        "facts_all": all(_contains_term(answer, term) for term in case.expected_all),
        "facts_any": all(
            any(_contains_term(answer, term) for term in group)
            for group in case.expected_any_groups
        ),
        "forbidden": all(term not in answer for term in case.forbidden_terms),
        "citations": all(term in answer for term in case.expected_citations),
        "units": all(
            any(_contains_term(answer, term) for term in group)
            for group in case.expected_unit_groups
        ),
        "refusal": any(term in answer for term in REFUSAL_TERMS) if case.requires_refusal else True,
    }
    images = extract_markdown_images(answer)
    image_results = [
        {"url": image["url"], "valid": valid, "error": error}
        for image in images
        for valid, error in [validate_image_reference(image["url"])]
    ]
    checks["image_present"] = bool(images) if case.requires_image else True
    checks["image_routes"] = (
        all(item["valid"] for item in image_results) if images else not case.requires_image
    )
    unsupported_citations: dict[str, Any] = {}
    if trace is not None:
        checks["citation_grounded"], unsupported_citations = validate_trace_citations(answer, trace)
        if case.requires_refusal:
            unsupported_citations["clauses"] = []
            unsupported_citations["tables"] = []
            checks["citation_grounded"] = not unsupported_citations["codes"]
        offered = set(trace.get("image_urls", []))
        offered_paths = {unquote(urlparse(url).path) for url in offered}
        checks["image_offered"] = all(
            unquote(urlparse(image["url"]).path) in offered_paths for image in images
        )
    if image_probe is not None:
        for item in image_results:
            http_valid, http_error = image_probe(item["url"])
            item["http_valid"] = http_valid
            item["http_error"] = http_error
        checks["image_http"] = (
            all(item.get("http_valid") for item in image_results)
            if images
            else not case.requires_image
        )
    failed_checks = [name for name, passed in checks.items() if not passed]
    return {
        "id": case.id,
        "query": case.query,
        "type": case.type,
        "passed": not failed_checks,
        "checks": checks,
        "failed_checks": failed_checks,
        "images": image_results,
        "unsupported_citations": unsupported_citations,
        "answer": answer,
    }


def run_answer_evaluation(
    *,
    api_base: str,
    api_key: str,
    path: Path = ANSWER_EVAL_PATH,
    progress_callback: Any = None,
) -> dict[str, Any]:
    import httpx

    cases = load_answer_cases(path)
    case_results: list[dict[str, Any]] = []
    image_cache: dict[str, tuple[bool, str]] = {}
    with httpx.Client(timeout=240) as client:
        for index, case in enumerate(cases, start=1):
            started = time.monotonic()
            try:
                response = client.post(
                    f"{api_base.rstrip('/')}/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
                    json={
                        "messages": [{"role": "user", "content": case.query}],
                        "stream": False,
                        "temperature": 0,
                        "top_p": 1,
                        "include_rag_trace": True,
                    },
                )
                response.raise_for_status()
                payload = response.json()
                answer = str(payload["choices"][0]["message"]["content"])
                trace = payload.get("rag_trace", {})
                result = evaluate_answer(
                    case,
                    answer,
                    trace=trace,
                    image_probe=lambda url: probe_image_url(
                        url,
                        api_base,
                        cache=image_cache,
                    ),
                )
                result["latency_seconds"] = round(time.monotonic() - started, 2)
            except Exception as exc:
                result = {
                    "id": case.id,
                    "query": case.query,
                    "type": case.type,
                    "passed": False,
                    "checks": {"request": False},
                    "failed_checks": ["request"],
                    "images": [],
                    "unsupported_citations": {},
                    "answer": "",
                    "error": str(exc),
                    "latency_seconds": round(time.monotonic() - started, 2),
                }
            case_results.append(result)
            if progress_callback:
                progress_callback(index, len(cases), result)
    result = summarize_answer_results(cases, case_results, path=path)
    result["api_base"] = api_base.rstrip("/")
    return result


def summarize_answer_results(
    cases: list[AnswerEvaluationCase],
    case_results: list[dict[str, Any]],
    *,
    path: Path = ANSWER_EVAL_PATH,
) -> dict[str, Any]:
    total = len(cases)
    passed = sum(1 for item in case_results if item.get("passed"))
    request_failures = [
        item for item in case_results if item.get("checks", {}).get("request") is False
    ]
    check_names = sorted({name for item in case_results for name in item.get("checks", {})})
    check_rates = {
        name: (
            sum(1 for item in case_results if item.get("checks", {}).get(name)) / total
            if total
            else 0
        )
        for name in check_names
    }
    by_type: dict[str, dict[str, int]] = {}
    for item in case_results:
        bucket = by_type.setdefault(item["type"], {"case_count": 0, "passed_count": 0})
        bucket["case_count"] += 1
        bucket["passed_count"] += int(item["passed"])
    manifest = read_active_manifest()
    refusal_results = [
        result for case, result in zip(cases, case_results, strict=True) if case.requires_refusal
    ]
    result = {
        "ok": not request_failures,
        "generated_at": datetime.now(UTC).isoformat(),
        "evaluation_set": str(path.resolve()),
        "evaluation_set_hash": hashlib.sha256(path.read_bytes()).hexdigest(),
        "data_version_hash": manifest.get("data_version_hash", ""),
        "case_count": total,
        "passed_count": passed,
        "failure_count": total - passed,
        "pass_rate": passed / total if total else 0,
        "check_rates": check_rates,
        "refusal_case_count": len(refusal_results),
        "refusal_pass_rate": (
            sum(1 for item in refusal_results if item.get("checks", {}).get("refusal"))
            / len(refusal_results)
            if refusal_results
            else 1
        ),
        "cases_by_type": by_type,
        "failures": [item for item in case_results if not item.get("passed")],
        "results": case_results,
    }
    if request_failures:
        sample_error = str(request_failures[0].get("error") or "请求失败")
        result["error"] = (
            f"回答级盲测有 {len(request_failures)}/{total} 个请求未完成；首个错误：{sample_error}"
        )
    return result


def render_answer_evaluation_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# 回答级盲测评估报告",
        "",
        f"- 评估集标识：`{result.get('evaluation_set_id', '-')}`",
        f"- 执行状态：{'完成' if result.get('ok') else '失败'}",
        f"- 目标 API：{result.get('api_base', '-')}",
        f"- 用例数：{result.get('case_count', 0)}",
        f"- 通过数：{result.get('passed_count', 0)}",
        f"- 总体通过率：{result.get('pass_rate', 0):.1%}",
        f"- 图片引用完整率：{result.get('check_rates', {}).get('image_routes', 0):.1%}",
        f"- 规范依据命中率：{result.get('check_rates', {}).get('citations', 0):.1%}",
        f"- 拒答正确率：{result.get('refusal_pass_rate', 0):.1%}",
        "",
    ]
    if result.get("error"):
        lines.extend(["## 执行错误", "", str(result["error"]), ""])
    lines.extend(["## 失败用例", ""])
    failures = result.get("failures", [])
    if not failures:
        lines.append("无失败用例。")
    for failure in failures:
        lines.extend(
            [
                f"### {failure.get('id')}",
                "",
                f"- 问题：{failure.get('query')}",
                f"- 失败检查：{', '.join(failure.get('failed_checks', []))}",
                "",
                "```text",
                str(failure.get("answer", "")).strip(),
                "```",
                "",
            ]
        )
    return "\n".join(lines) + "\n"
