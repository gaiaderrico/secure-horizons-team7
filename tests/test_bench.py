from mirage.bench.run_bench import run_bench, to_csv, render_markdown


def test_detection_and_false_positive_rates():
    rows, s = run_bench()
    by = {r.scenario: r for r in rows}
    # all four attacks raise an incident; benign/backup do not
    assert by["ai_agent"].detected and by["ai_agent"].label == "ai_agent"
    assert by["ai_guided"].label == "ai_guided_by_human"
    assert by["script"].detected and by["human"].detected
    assert not by["benign_user"].detected and not by["backup_job"].detected
    assert s["detection_rate"] == 1.0
    assert s["false_positive_rate"] == 0.0
    # human opened a crown jewel while real, before the mine
    assert by["human"].real_lost == 1
    assert s["real_files_lost_total"] == 1


def test_outputs_nonempty():
    rows, s = run_bench()
    assert "scenario,is_intruder" in to_csv(rows)
    md = render_markdown(rows, s)
    assert "Detection rate" in md and "note-follow rate" in md
