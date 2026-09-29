"""Contract checks for coworld-ab's paired, head-to-head and sequential statistics."""
import importlib.util
import math
import sys
from pathlib import Path

import pytest
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / '.claude/skills/coworld-ab/scripts'


def module(name, path):
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ab = module('ab_stats', SCRIPTS / 'ab_stats.py')
ps = module('paired_stats', SCRIPTS / 'paired_stats.py')

METRIC = [('score', True, 'mean', None)]
value_of = lambda row, key: row.get(key)  # noqa: E731


def pairs(base, cand, key='score'):
    return {'all': [({key: b}, {key: c}) for b, c in zip(base, cand)]}


def test_paired_t_and_wilcoxon_match_scipy():
    base = [0.4, 0.5, 0.45, 0.6, 0.55, 0.3, 0.5, 0.52]
    cand = [0.5, 0.55, 0.44, 0.7, 0.6, 0.41, 0.58, 0.5]
    t, p, dz, w_p = ps.paired_mean_sig(base, cand)
    ref = stats.ttest_rel(cand, base)
    diffs = [c - b for b, c in zip(base, cand)]
    assert (t, p) == pytest.approx((ref.statistic, ref.pvalue))
    assert w_p == pytest.approx(stats.wilcoxon(diffs).pvalue)
    assert dz == pytest.approx(sum(diffs) / len(diffs) / stats.tstd(diffs))
    assert ps.paired_mean_sig([1, 2, 3], [2, 3, 4])[1] == 1.0  # constant difference: no test


def test_mcnemar_uses_only_discordant_pairs_and_draw_is_non_win():
    base = [1] * 2 + [0] * 10
    cand = [0] * 2 + [1] * 10
    effect, p, b, c = ps.mcnemar_sig(base, cand)
    assert (b, c) == (2, 10)
    assert p == pytest.approx(stats.binomtest(10, 12, 0.5).pvalue)
    # Concordant pairs (both won, or both did not win, e.g. both drew) leave p unchanged.
    _, p_more, _, _ = ps.mcnemar_sig(base + [1] * 5 + [0] * 7, cand + [1] * 5 + [0] * 7)
    assert p_more == pytest.approx(p)
    assert effect == pytest.approx(8 / 12)
    with pytest.raises(ValueError):
        ps.mcnemar_sig([0.5], [1])


def test_head_to_head_one_sample_and_decisive_binomial():
    scores = [0.6, 0.75, 0.4, 0.9, 0.55, 0.65]
    t, p, d = ps.one_sample_sig(scores, 0.5)
    ref = stats.ttest_1samp(scores, 0.5)
    assert (t, p) == pytest.approx((ref.statistic, ref.pvalue))
    effect, p = ps.decisive_binomial(9, 3)
    assert effect == pytest.approx(9 / 12 - 0.5)
    assert p == pytest.approx(stats.binomtest(9, 12, 0.5).pvalue)
    # Within an episode: candidate win (0,1), candidate loss (1,0), draw (0,0) drops out.
    d = ps.PairedDelta('win_rate', 'all', True, 0.25, 0.5, 4, 4, 'rate')
    d.compute_pairs([0, 1, 0, 0], [1, 0, 1, 0], 'decisive_binomial')
    assert d.detail == {'candidate_wins': 2, 'candidate_losses': 1, 'draws': 1}
    assert d.p == pytest.approx(stats.binomtest(2, 3, 0.5).pvalue)


def test_small_n_floor_blocks_directional_verdicts():
    base = [0.4 + 0.01 * (i % 5) for i in range(40)]
    cand = [b + 0.1 + 0.01 * (i % 3) for i, b in enumerate(base)]
    few = ps.build_paired_deltas(pairs(base[:20], cand[:20]), METRIC, value_of, ['all'])[0]
    assert few.raw_p < 0.001 and few.verdict == 'inconclusive'
    many = ps.build_paired_deltas(pairs(base, cand), METRIC, value_of, ['all'])[0]
    assert many.verdict == 'improved' and many.n_base == 40
    wins = ps.build_paired_deltas(pairs([0] * 20, [1] * 20, 'w'), [('w', True, 'rate', None)], value_of, ['all'])[0]
    assert wins.raw_p < 0.001 and wins.verdict == 'inconclusive'


def test_wilcoxon_must_agree(monkeypatch):
    base = [0.4 + 0.01 * (i % 5) for i in range(40)]
    cand = [b + 0.1 + 0.01 * (i % 3) for i, b in enumerate(base)]
    monkeypatch.setattr(ps, 'wilcoxon_p', lambda diffs: 0.5)
    d = ps.build_paired_deltas(pairs(base, cand), METRIC, value_of, ['all'])[0]
    assert d.raw_p < 0.001 and d.verdict == 'inconclusive'
    assert d.detail['wilcoxon_p'] == 0.5


def test_by_correction_and_missing_values_counted():
    metrics = [(f'm{i}', True, 'mean', None) for i in range(5)]
    rows = [({f'm{i}': j * (i + 1) % 7 for i in range(5)}, {f'm{i}': (j * (i + 1) + i + j % 3) % 7 for i in range(5)})
            for j in range(35)]
    rows[0][1]['m0'] = None  # unknown stays out of the test, never becomes 0
    deltas = ps.build_paired_deltas({'all': rows}, metrics, value_of, ['all'])
    tested = [d for d in deltas if d.base is not None]
    adjusted = stats.false_discovery_control([d.raw_p for d in tested], method='by')
    assert [d.p for d in tested] == pytest.approx(list(adjusted))
    assert deltas[0].n_base == 34 and deltas[1].n_base == 35


def test_emit_json_keeps_neutral_contract_and_adds_test():
    deltas = ps.build_paired_deltas(pairs([0.4] * 3 + [0.5], [0.5] * 3 + [0.7]), METRIC, value_of, ['all'])
    report = ps.emit_json('base', 'cand', 'score', deltas)
    row = report['deltas'][0]
    assert {'metric', 'group', 'base', 'cand', 'n_base', 'n_cand', 'p', 'raw_p', 'effect', 'verdict'} <= set(row)
    assert row['test'] == 'paired_t' and 'wilcoxon_p' in row['detail']
    assert report['analysis'] == ps.PAIRED_ANALYSIS


def test_sprt_bounds_llr_and_decisions():
    lower, upper = ps.sprt_bounds(0.05, 0.05)
    assert (lower, upper) == pytest.approx((math.log(0.05 / 0.95), math.log(0.95 / 0.05)))
    r = ps.sprt(0.03, 0.0001, 40, h0=0, h1=0.05)
    assert r.llr == pytest.approx(((0.03) ** 2 - (0.03 - 0.05) ** 2) / 0.0002)  # 2.5: inside the bounds
    assert r.decision == 'continue'
    assert ps.sprt(0.05, 0.0001, 40, h0=0, h1=0.05).decision == 'accept_h1'  # LLR 12.5
    strong_null = ps.sprt_mean([0.01 * ((i % 7) - 3) for i in range(200)], h0=0, h1=0.05)
    assert strong_null.decision == 'accept_h0'
    # The floor: a huge LLR below SMALL_N observations is still "continue".
    early = ps.sprt_mean([0.2 + 0.01 * (i % 3) for i in range(10)], h0=0, h1=0.05)
    assert early.llr > upper and early.decision == 'continue' and 'floor' in early.note
    assert ps.sprt_mean([0.1] * 40, h0=0, h1=0.05).decision == 'continue'  # no variance
    two = ps.sprt_two_sample([0.5, 0.4, 0.6] * 12, [0.6, 0.5, 0.7] * 12, h0=0, h1=0.05)
    assert two.estimate == pytest.approx(0.1) and two.n == 36
    with pytest.raises(ValueError):
        ps.sprt(0.0, 1.0, 40, h0=0.05, h1=0.05)


def test_ab_stats_correction_refactor_is_shared():
    d = ab.Delta('win', 'all', True, 0.2, 0.8, 100, 100, 'rate')
    d.compute([], [])
    ab.apply_correction([d])
    assert d.p == pytest.approx(d.raw_p) and d.verdict == 'improved'
    assert ab.emit_json('a', 'b', None, [d])['analysis'] == ab.INDEPENDENT_ANALYSIS
