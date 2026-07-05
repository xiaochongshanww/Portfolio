import json
from pathlib import Path

from src.app.rag.structured_tables import (
    find_structured_table_matches,
    format_structured_table_context,
    load_structured_tables,
)
from src.evaluation.runner import STRUCTURED_EVAL_PATH, load_cases, render_evaluation_markdown, run_evaluation


def test_structured_table_files_load():
    tables = load_structured_tables()
    table_ids = {table["source"]["table_id"] for table in tables}
    assert "3.2.5" in table_ids
    assert "5.1.1" in table_ids
    assert "5.1.2" in table_ids
    assert "5.3.1" in table_ids
    assert "5.3.2" in table_ids
    assert "7.1.1" in table_ids
    assert "8.1.1" in table_ids
    assert "8.2.1" in table_ids


def test_live_load_lookup_prefers_exact_alias_row():
    matches = find_structured_table_matches("办公楼的楼面活荷载标准值取多少？")
    assert matches
    top = matches[0]
    assert top.table["source"]["table_id"] == "5.1.1"
    assert top.row["standard_value"] == 2.0
    assert "办公楼" in top.matched_terms
    context = format_structured_table_context(top)
    assert "结构化表格命中：true" in context
    assert "表号：5.1.1" in context
    assert "标准值：2.0 kN/m²" in context


def test_live_load_lookup_distinguishes_other_balcony():
    matches = find_structured_table_matches("其他阳台的楼面活荷载标准值取多少？")
    assert matches
    top = matches[0]
    assert top.row["condition"] == "其他"
    assert top.row["standard_value"] == 2.5


def test_live_load_lookup_covers_machine_room_row():
    matches = find_structured_table_matches("电梯机房楼面活荷载标准值是多少？")
    assert matches
    top = matches[0]
    assert top.table["source"]["table_id"] == "5.1.1"
    assert top.row["item_no"] == "7"
    assert top.row["standard_value"] == 7.0


def test_live_load_lookup_distinguishes_fire_truck_span_condition():
    matches = find_structured_table_matches("6m×6m无梁楼盖消防车活荷载标准值是多少？")
    assert matches
    top = matches[0]
    assert top.row["item_no"] == "8(2)-消防车"
    assert top.row["standard_value"] == 20.0


def test_live_load_lookup_distinguishes_other_kitchen():
    matches = find_structured_table_matches("其他厨房楼面活荷载标准值是多少？")
    assert matches
    top = matches[0]
    assert top.row["item_no"] == "9(2)"
    assert top.row["standard_value"] == 2.0


def test_live_load_lookup_distinguishes_office_corridor():
    matches = find_structured_table_matches("办公楼走廊活荷载标准值是多少？")
    assert matches
    top = matches[0]
    assert top.row["item_no"] == "11(2)"
    assert top.row["standard_value"] == 2.5


def test_live_load_lookup_distinguishes_other_stair():
    matches = find_structured_table_matches("其他楼梯活荷载标准值是多少？")
    assert matches
    top = matches[0]
    assert top.row["item_no"] == "12(2)"
    assert top.row["standard_value"] == 3.5


def test_live_load_reduction_table_lookup_by_table_name():
    matches = find_structured_table_matches("活荷载按楼层的折减系数应查哪个表？")
    assert matches
    top = matches[0]
    assert top.table["source"]["table_id"] == "5.1.2"
    assert top.table["source"]["table_name"] == "活荷载按楼层的折减系数"


def test_live_load_reduction_lookup_by_floor_range():
    matches = find_structured_table_matches("墙柱基础计算截面以上9到20层时活荷载折减系数是多少？")
    assert matches
    top = matches[0]
    assert top.table["source"]["table_id"] == "5.1.2"
    assert top.row["supported_levels"] == "9~20"
    assert top.row["reduction_factor"] == 0.6


def test_design_life_adjustment_factor_lookup():
    matches = find_structured_table_matches("结构设计使用年限100年时楼面屋面活荷载调整系数是多少？")
    assert matches
    top = matches[0]
    assert top.table["source"]["table_id"] == "3.2.5"
    assert top.row["design_working_life_years"] == 100
    assert top.row["adjustment_factor_gamma_l"] == 1.1


def test_roof_live_load_lookup_distinguishes_non_accessible_roof():
    matches = find_structured_table_matches("不上人屋面均布活荷载标准值是多少？")
    assert matches
    top = matches[0]
    assert top.table["source"]["table_id"] == "5.3.1"
    assert top.row["category"] == "不上人的屋面"
    assert top.row["standard_value"] == 0.5


def test_roof_live_load_lookup_distinguishes_accessible_roof():
    matches = find_structured_table_matches("上人屋面均布活荷载标准值是多少？")
    assert matches
    top = matches[0]
    assert top.table["source"]["table_id"] == "5.3.1"
    assert top.row["category"] == "上人的屋面"
    assert top.row["standard_value"] == 2.0


def test_roof_garden_live_load_lookup():
    matches = find_structured_table_matches("屋顶花园活荷载标准值取多少？")
    assert matches
    top = matches[0]
    assert top.table["source"]["table_id"] == "5.3.1"
    assert top.row["category"] == "屋顶花园"
    assert top.row["standard_value"] == 3.0


def test_helicopter_roof_local_load_lookup():
    matches = find_structured_table_matches("轻型屋面直升机停机坪局部荷载标准值和作用面积是多少？")
    assert matches
    top = matches[0]
    assert top.table["source"]["table_id"] == "5.3.2"
    assert top.row["helicopter_type"] == "轻型"
    assert top.row["local_load_standard_value"] == 20
    assert top.row["action_area"] == "0.20m×0.20m"


def test_snow_load_formula_lookup_uses_structured_reference():
    matches = find_structured_table_matches("雪荷载标准值的计算公式是什么？")
    assert matches
    top = matches[0]
    assert top.table["source"]["table_id"] == "7.1.1"
    assert top.row["formula_latex"] == "s_k = \\mu_r s_0"
    context = format_structured_table_context(top)
    assert "雪荷载标准值 = 屋面积雪分布系数 × 基本雪压" in context


def test_wind_load_formula_lookup_distinguishes_main_structure():
    matches = find_structured_table_matches("主要受力结构风荷载标准值如何计算？")
    assert matches
    top = matches[0]
    assert top.table["source"]["table_id"] == "8.1.1"
    assert top.row["case"] == "主要受力结构"
    assert top.row["formula_latex"] == "w_k = \\beta_z \\mu_s \\mu_z w_0"


def test_wind_load_formula_lookup_distinguishes_cladding():
    matches = find_structured_table_matches("围护结构风荷载标准值计算公式是什么？")
    assert matches
    top = matches[0]
    assert top.table["source"]["table_id"] == "8.1.1"
    assert top.row["case"] == "围护结构"
    assert top.row["formula_latex"] == "w_k = \\beta_g \\mu_{sl} \\mu_z w_0"


def test_wind_pressure_height_factor_lookup():
    matches = find_structured_table_matches("B类地面粗糙度100m风压高度变化系数是多少？")
    assert matches
    top = matches[0]
    assert top.table["source"]["table_id"] == "8.2.1"
    assert top.row["height"] == "100"
    assert top.row["roughness_b"] == 2.00


def test_structured_evaluation_suite_passes_and_renders_markdown():
    cases = load_cases(STRUCTURED_EVAL_PATH)
    result = run_evaluation(STRUCTURED_EVAL_PATH, top_k=5)
    markdown = render_evaluation_markdown(result, "结构化检索专项评估")

    assert len(cases) == 12
    assert result["ok"] is True
    assert result["generated_at"]
    assert len(result["evaluation_set_hash"]) == 64
    assert result["data_version_hash"]
    assert result["structured_table_hit_rate"] == 1.0
    assert result["failures"] == []
    assert "# 结构化检索专项评估" in markdown
    assert "结构化表命中率：100.0%" in markdown


def test_structured_table_5_1_2_file_shape():
    path = Path("data/structured_tables/GB_50009_2012_table_5_1_2_live_load_reduction.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["source"]["code"] == "GB 50009-2012"
    assert payload["source"]["table_id"] == "5.1.2"
    assert any(row["supported_levels"] == ">20" and row["reduction_factor"] == 0.55 for row in payload["rows"])


def test_structured_table_5_1_1_file_shape_contains_completed_rows():
    path = Path("data/structured_tables/GB_50009_2012_table_5_1_1_live_loads.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload["rows"]

    def find_by_alias(alias: str):
        return [row for row in rows if alias in row.get("aliases", [])]

    assert find_by_alias("电梯机房")[0]["standard_value"] == 7.0
    assert find_by_alias("办公楼走廊")[0]["standard_value"] == 2.5
    assert find_by_alias("其他楼梯")[0]["standard_value"] == 3.5
    assert any(row["item_no"] == "8(2)-消防车" and row["standard_value"] == 20.0 for row in rows)


def test_roof_structured_table_files_shape():
    table_3_2_5 = json.loads(
        Path("data/structured_tables/GB_50009_2012_table_3_2_5_live_load_design_life_factor.json").read_text(
            encoding="utf-8"
        )
    )
    table_5_3_1 = json.loads(
        Path("data/structured_tables/GB_50009_2012_table_5_3_1_roof_live_loads.json").read_text(encoding="utf-8")
    )
    table_5_3_2 = json.loads(
        Path("data/structured_tables/GB_50009_2012_table_5_3_2_helicopter_roof_loads.json").read_text(
            encoding="utf-8"
        )
    )

    assert any(row["design_working_life_years"] == 5 and row["adjustment_factor_gamma_l"] == 0.9 for row in table_3_2_5["rows"])
    assert any(row["category"] == "屋顶运动场地" and row["quasi_permanent_factor"] == 0.4 for row in table_5_3_1["rows"])
    assert any(row["helicopter_type"] == "重型" and row["local_load_standard_value"] == 60 for row in table_5_3_2["rows"])


def test_snow_wind_structured_reference_files_shape():
    snow_formula = json.loads(
        Path("data/structured_tables/GB_50009_2012_clause_7_1_1_snow_load_formula.json").read_text(
            encoding="utf-8"
        )
    )
    wind_formula = json.loads(
        Path("data/structured_tables/GB_50009_2012_clause_8_1_1_wind_load_formula.json").read_text(
            encoding="utf-8"
        )
    )
    wind_height = json.loads(
        Path("data/structured_tables/GB_50009_2012_table_8_2_1_wind_pressure_height_factor.json").read_text(
            encoding="utf-8"
        )
    )

    assert snow_formula["source"]["clause_number"] == "7.1.1"
    assert snow_formula["rows"][0]["formula_latex"] == "s_k = \\mu_r s_0"
    assert {row["case"] for row in wind_formula["rows"]} == {"主要受力结构", "围护结构"}
    assert any(row["height"] == "≥550" and row["roughness_d"] == 2.91 for row in wind_height["rows"])
