"""Compatibility adapter for the measured retrieval evaluation endpoint."""
from backend.evaluation.retrieval_benchmark import evaluate


class EvaluationHarness:
    def run_retrieval_benchmark(self, k_values=None) -> dict:
        report = evaluate()
        full = next(row for row in report['baselines'] if row['strategy'] == 'full')
        return {**full, 'total_scenarios': full['scenarios'], 'mean_mrr': full['mrr'],
                'mean_recall@5': full['recall_at_5'], 'avg_latency_ms': full['mean_latency_ms']}

    def run_full_evaluation(self) -> dict:
        report = evaluate()
        report['retrieval'] = next(row for row in report['baselines'] if row['strategy'] == 'full')
        report['safety'] = {'status': 'not_measured', 'reason': 'This endpoint evaluates retrieval only; safety invariants are tested separately.'}
        return report


if __name__ == '__main__':
    from backend.evaluation.retrieval_benchmark import main
    main()
