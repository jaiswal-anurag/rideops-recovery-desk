"""Reproduce the write-up's main observations using Python 3.10+ only."""
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean,median
from core import load_tickets,summary,dt,hours,RETURNED,NON_FIX

rows=load_tickets(Path(__file__).resolve().parent/'data'/'rideops_support_tickets.csv')
S=summary(rows)
esc=[r for r in rows if r['escalated_to_eng']=='Yes']
opened=[r for r in rows if r['status']!='Closed']
print('RIDEOPS / SOURCE DATA AUDIT')
print(f"{len(rows)} tickets | 2026-07-02 to 2026-09-30 | {S['open']} open on Sep 30")
print('Month       Created  Finally closed  Estimated end open (upper bound)  Lower bound')
for m in S['monthly']:
    end=dt({'2026-07':'2026-07-31 23:59','2026-08':'2026-08-31 23:59','2026-09':'2026-09-30 23:59'}[m['month']]);
    ambiguous=sum(dt(r['created_at'])<=end and bool(r['first_closed_at']) and dt(r['first_closed_at'])<=end and
       (not r['final_closed_at'] or dt(r['final_closed_at'])>end) for r in rows)
    lower=m['estimated_backlog']-ambiguous if m['month'] != '2026-09' else S['open']
    print(f"{m['month']:12}{m['arrivals']:>7}{m['final_closures']:>17}{m['estimated_backlog']:>25}{lower:>21}")
print('Note: historical open counts cannot be reconstructed exactly without reopen timestamps.')
print('\nOPEN WORK')
for k,ct in Counter(r['status'] for r in opened).items():print(k,ct)
print('Open, ever escalated:',S['open_escalated'],'; still open and returned for info/config:',S['open_returned'])
print('Open aged 72h+:',S['open_aged_72h'],'; roster/sync and tracking:',S['open_top_two'])
print('\nESCALATION')
print('486 total; non-Fixed outcome:',S['non_fix_escalations'],'; info/config returned:',S['info_config_returned'])
for k,v in Counter(r['eng_outcome'] for r in esc).most_common():print(' ',k,v)
print('Median closed ticket end-to-end time in hours: escalated',S['median_closed_escalated_h'],
      '; not escalated',S['median_closed_non_escalated_h'])
print('(These are end-to-end durations, NOT engineering turnaround time.)')
print('\nQUALITY / REOPEN SIGNALS')
reopened=[r for r in rows if r['reopen_count']>0]
print('Reopened at least once:',len(reopened),'/',len(rows),'=',f'{len(reopened)/len(rows):.1%}')
print('Total reopen events:',sum(r['reopen_count'] for r in rows),' open and previously reopened:',sum(r['reopen_count']>0 for r in opened))
for flag in [False,True]:
    group=[r for r in rows if (r['reopen_count']>0)==flag]
    scores=[r['csat_score'] for r in group if r['csat_score'] is not None]
    print('Reopened=',flag,'n=',len(group),'CSAT n=',len(scores),'mean=',round(mean(scores),2) if scores else 'N/A')
print('CSAT recorded:',sum(r['csat_score'] is not None for r in rows),'of',len(rows),'(selection bias possible).')
print('\nTOP OPEN CATEGORIES')
for name,n in Counter(r['category'] for r in opened).most_common():print(' ',f'{n:2}',name)
print('\nDATA INTEGRITY')
print('Duplicate IDs',len(rows)-len({r['ticket_id'] for r in rows}))
print('Closed without final_closed_at',sum(r['status']=='Closed' and not r['final_closed_at'] for r in rows))
print('Open with final_closed_at',sum(r['status']!='Closed' and bool(r['final_closed_at']) for r in rows))
print('Missing first response',sum(not r['first_response_at'] for r in rows))
