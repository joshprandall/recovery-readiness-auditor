#!/usr/bin/env python3
"""Offline recovery-readiness checks against a declared service inventory."""
import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = {'service','owner','rpo_hours','rto_hours','last_backup_utc','last_restore_test_utc','runbook_url'}

def timestamp(value):
    """Require timezone-aware ISO 8601; normalize to UTC."""
    parsed = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('timestamp must include a timezone offset or Z')
    return parsed.astimezone(timezone.utc)

def positive(value):
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError('must be a finite number greater than zero')
    return result

def evaluate(row, now, restore_days=90):
    """A finding indicates a recorded gap, not proof of an outage."""
    findings=[]
    def add(code, severity, detail):
        findings.append({'code':code,'severity':severity,'detail':detail})
    name=(row.get('service') or '').strip()
    if not name: add('MISSING_SERVICE','error','Service name is required.')
    if not (row.get('owner') or '').strip(): add('MISSING_OWNER','warning','No accountable owner is recorded.')
    rpo=None
    for field in ['rpo_hours','rto_hours']:
        try:
            value=positive(row.get(field) or '')
            if field=='rpo_hours': rpo=value
        except (ValueError,TypeError):
            add('INVALID_'+field.upper(),'error',f'{field} must be a finite number greater than zero.')
    for field in ['last_backup_utc','last_restore_test_utc']:
        raw=(row.get(field) or '').strip()
        if not raw:
            add('MISSING_'+field.upper(),'error' if field=='last_backup_utc' else 'warning',f'{field} is not recorded.')
            continue
        try: age=(now-timestamp(raw)).total_seconds()/3600
        except (ValueError,TypeError):
            add('INVALID_'+field.upper(),'error',f'{field} must be a timezone-aware ISO 8601 timestamp.')
            continue
        if age<0:
            add('FUTURE_'+field.upper(),'error',f'{field} is later than the audit time.')
        elif field=='last_backup_utc' and rpo is not None and age>rpo:
            add('BACKUP_EXCEEDS_RPO','error',f'Latest recorded backup is {age:.1f} hours old; declared RPO is {rpo:g} hours.')
        elif field=='last_restore_test_utc' and age>restore_days*24:
            add('RESTORE_TEST_OVERDUE','warning',f'Latest recorded restore test is {age/24:.1f} days old; policy is {restore_days} days.')
    if not (row.get('runbook_url') or '').strip(): add('MISSING_RUNBOOK','warning','No recovery runbook reference is recorded.')
    return {'service':name or '(unnamed)','owner':(row.get('owner') or '').strip(),'status':'attention' if findings else 'no_recorded_gaps','findings':findings}

def audit(path, now, restore_days):
    with Path(path).open(newline='',encoding='utf-8-sig') as stream:
        reader=csv.DictReader(stream)
        missing=REQUIRED-set(reader.fieldnames or [])
        if missing: raise ValueError('Missing CSV columns: '+', '.join(sorted(missing)))
        if len(reader.fieldnames)!=len(set(reader.fieldnames)): raise ValueError('Duplicate CSV column names.')
        rows=list(reader)
    if not rows: raise ValueError('The inventory has no service rows.')
    results=[]
    names=set()
    for row in rows:
        if None in row or any(v is None for v in row.values()): raise ValueError('A CSV row has too many or too few fields.')
        result=evaluate(row,now,restore_days)
        key=result['service'].casefold()
        if key in names: raise ValueError('Duplicate service name: '+result['service'])
        names.add(key)
        results.append(result)
    return {'audited_at':now.isoformat(),'restore_test_policy_days':restore_days,'service_count':len(results),'services_with_findings':sum(bool(r['findings']) for r in results),'services':results}

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inventory',type=Path)
    parser.add_argument('--as-of',help='Timezone-aware ISO 8601 audit time; default is current UTC')
    parser.add_argument('--restore-days',type=int,default=90)
    parser.add_argument('--format',choices=['text','json'],default='text')
    args=parser.parse_args(argv)
    try:
        if args.restore_days<=0: raise ValueError('--restore-days must be greater than zero')
        now=timestamp(args.as_of) if args.as_of else datetime.now(timezone.utc)
        report=audit(args.inventory,now,args.restore_days)
    except (OSError,ValueError,csv.Error) as exc:
        print('Input error: '+str(exc),file=sys.stderr)
        return 2
    if args.format=='json': print(json.dumps(report,indent=2))
    else:
        print(f"RECOVERY READINESS | {report['audited_at']}")
        print(f"{report['services_with_findings']} of {report['service_count']} services have recorded gaps.\n")
        for service in report['services']:
            print(service['service']+' — '+service['status'])
            for finding in service['findings']:
                print(f"  {finding['severity'].upper()}: {finding['code']} — {finding['detail']}")
    return 1 if report['services_with_findings'] else 0

if __name__=='__main__': sys.exit(main())
