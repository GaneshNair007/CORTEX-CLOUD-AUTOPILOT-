"""Safe provider doctor. --live performs one bounded inference request."""
from pathlib import Path
import argparse
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--provider', choices=['nvidia','gemini','cheaperinference','openai','anthropic','ollama','heuristic'])
    parser.add_argument('--live', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.provider:
        os.environ['LLM_PRIMARY_PROVIDER'] = args.provider
    from backend.config.settings import settings
    cfg = settings.llm
    report = {'provider': cfg.provider.upper(), 'model': cfg.active_model,
              'credential': 'CONFIGURED' if cfg.credential_present else 'NOT_CONFIGURED',
              'live_test': False, 'status': 'CONFIGURED' if cfg.credential_present or cfg.provider in ('ollama','heuristic') else 'UNAVAILABLE'}
    if args.live:
        if cfg.provider == 'heuristic' or (cfg.provider != 'ollama' and not cfg.credential_present):
            report['status'] = 'FAILED'
            report['reason'] = 'A fresh external-provider credential must be configured locally first'
        else:
            from backend.llm.client import LLMClient
            try:
                result = LLMClient().generate('Reply exactly CORTEX_OK', system='Return only the requested test string.',
                                               max_tokens=32, temperature=0, incident_id='PROVIDER-SMOKE', purpose='smoke_test')
                success = result['provider'] == cfg.provider and not result['fallback_used'] and result['text'].strip() == 'CORTEX_OK'
                report.update(live_test=True, status='SUCCESS' if success else 'FAILED',
                              actual_provider=result['provider'], actual_model=result['model'],
                              latency_ms=result['latency_ms'], input_tokens=result.get('input_tokens'),
                              output_tokens=result.get('output_tokens'), fallback_used=result['fallback_used'],
                              response='CORTEX_OK' if success else 'Unexpected response or fallback; content withheld')
            except Exception as exc:
                report.update(status='FAILED', error_code=getattr(exc, 'error_code', type(exc).__name__))
    print(json.dumps(report, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2)+'\n')
    return 0 if report['status'] in ('SUCCESS','CONFIGURED') else 2


if __name__ == '__main__':
    raise SystemExit(main())
