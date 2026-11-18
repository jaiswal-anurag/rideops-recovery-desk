"""RideOps Recovery Desk. Run: python app.py (Python 3.10+; no pip install)."""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sqlite3
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from core import load_tickets, summary, ticket_view, validate_packet, packet_as_text, write_csv

ROOT=Path(__file__).resolve().parent
DEFAULT_CSV=ROOT / "data" / "rideops_support_tickets.csv"
VALID_ACTIONS={"client_updated","basic_checks_done","owner_confirmed","handoff_sent","verified_resolved"}


def initialize_db(db_path:Path)->None:
    db_path.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id TEXT NOT NULL,
            action TEXT NOT NULL, note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS handoffs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id TEXT NOT NULL,
            packet_json TEXT NOT NULL, packet_text TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """)


def make_handler(tickets:list[dict],db_path:Path):
    by_id={r["ticket_id"]:r for r in tickets}
    queue=sorted([ticket_view(r) for r in tickets if r["status"]!="Closed"],key=lambda r:(-r["score"],r["created_at"]))
    stats=summary(tickets)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,format,*args):
            print(f"[{self.log_date_time_string()}] {format % args}")

        def send_data(self,data,status=200):
            body=json.dumps(data,ensure_ascii=False,default=str).encode("utf-8")
            self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Content-Length",str(len(body)));self.send_header("Cache-Control","no-store")
            self.end_headers();self.wfile.write(body)

        def send_csv(self,text,filename):
            body=text.encode('utf-8-sig');self.send_response(200)
            self.send_header('Content-Type','text/csv; charset=utf-8')
            self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)

        def send_static(self,name:str):
            path=ROOT/'web'/name
            if not path.is_file():return self.send_error(404)
            body=path.read_bytes();mime=mimetypes.guess_type(str(path))[0] or 'application/octet-stream'
            self.send_response(200);self.send_header('Content-Type',mime+'; charset=utf-8')
            self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)

        def do_GET(self):
            path=urlparse(self.path).path
            if path in ('/','/index.html'):return self.send_static('index.html')
            if path in ('/app.js','/styles.css'):return self.send_static(path[1:])
            if path=='/api/health':return self.send_data({'ok':True,'source':'static snapshot','tickets':len(tickets)})
            if path=='/api/state':
                with sqlite3.connect(db_path) as conn:
                    actions=conn.execute('SELECT id,ticket_id,action,note,created_at FROM actions ORDER BY id DESC').fetchall()
                    handoffs=conn.execute('SELECT ticket_id,COUNT(*) FROM handoffs GROUP BY ticket_id').fetchall()
                return self.send_data({'stats':stats,'queue':queue,
                   'activity':[dict(zip(['id','ticket_id','action','note','created_at'],r)) for r in actions],
                   'packets_saved':dict(handoffs),
                   'source_notice':'Historical 30 Sep 2026 snapshot. Logged actions never alter the original CSV or ticket system.'})
            if path.startswith('/api/ticket/'):
                tid=path.rsplit('/',1)[-1]
                if tid not in by_id:return self.send_data({'error':'Unknown ticket ID'},404)
                with sqlite3.connect(db_path) as conn:
                    actions=conn.execute('SELECT action,note,created_at FROM actions WHERE ticket_id=? ORDER BY id DESC',(tid,)).fetchall()
                    handoffs=conn.execute('SELECT id,packet_text,created_at FROM handoffs WHERE ticket_id=? ORDER BY id DESC',(tid,)).fetchall()
                return self.send_data({'ticket':ticket_view(by_id[tid]),
                   'activity':[dict(zip(['action','note','created_at'],x)) for x in actions],
                   'handoffs':[dict(zip(['id','packet_text','created_at'],x)) for x in handoffs]})
            if path=='/api/export/queue.csv':
                columns=['ticket_id','priority','score','age_days','lane','status','category','assigned_agent','client_name','eng_handoffs','reopen_count','eng_outcome','description','recommendation']
                return self.send_csv(write_csv(queue,columns),'rideops_open_triage_queue.csv')
            if path=='/api/export/actions.csv':
                with sqlite3.connect(db_path) as conn:
                    rs=conn.execute('SELECT ticket_id,action,note,created_at FROM actions ORDER BY id').fetchall()
                cols=['ticket_id','action','note','created_at']
                return self.send_csv(write_csv([dict(zip(cols,r)) for r in rs],cols),'rideops_action_log.csv')
            if path=='/api/export/handoffs.csv':
                with sqlite3.connect(db_path) as conn:
                    rs=conn.execute('SELECT ticket_id,packet_text,created_at FROM handoffs ORDER BY id').fetchall()
                cols=['ticket_id','packet_text','created_at']
                return self.send_csv(write_csv([dict(zip(cols,r)) for r in rs],cols),'rideops_handoff_packets.csv')
            return self.send_error(404)

        def do_POST(self):
            path=urlparse(self.path).path
            if path not in ('/api/action','/api/handoff'):return self.send_error(404)
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<65536:raise ValueError('Request must be smaller than 64 KB')
                data=json.loads(self.rfile.read(length).decode('utf-8'))
                if not isinstance(data,dict):raise ValueError('Expected JSON object')
                tid=str(data.get('ticket_id','')).strip()
                if tid not in by_id or by_id[tid]['status']=='Closed':raise ValueError('Unknown or non-open ticket')
                timestamp=datetime.now().astimezone().isoformat(timespec='seconds')
                if path=='/api/action':
                    action=str(data.get('action',''))
                    if action not in VALID_ACTIONS:raise ValueError('Unknown action type')
                    note=str(data.get('note','')).strip()[:2000]
                    if action=='verified_resolved' and len(note)<8:raise ValueError('Explain how the client-visible fix was verified')
                    with sqlite3.connect(db_path) as conn:
                        conn.execute('INSERT INTO actions (ticket_id,action,note,created_at) VALUES (?,?,?,?)',(tid,action,note,timestamp))
                    return self.send_data({'ok':True,'message':'Logged locally; source ticket status unchanged.'},201)
                info=validate_packet(data,set(by_id))
                packet=packet_as_text(by_id[tid],info)
                with sqlite3.connect(db_path) as conn:
                    conn.execute('INSERT INTO handoffs (ticket_id,packet_json,packet_text,created_at) VALUES (?,?,?,?)',(tid,json.dumps(info),packet,timestamp))
                return self.send_data({'ok':True,'packet':packet,'message':'Complete handoff packet saved locally; not sent to engineering.'},201)
            except (ValueError,UnicodeError,json.JSONDecodeError) as e:
                return self.send_data({'error':str(e)},400)
    return Handler


def main():
    parser=argparse.ArgumentParser(description='RideOps Recovery Desk, 30 Sep 2026 snapshot')
    parser.add_argument('--csv',type=Path,default=DEFAULT_CSV,help='Path to replacement CSV with same schema')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--db',type=Path,default=ROOT/'.local'/'recoverydesk.db')
    args=parser.parse_args()
    tickets=load_tickets(args.csv);initialize_db(args.db)
    srv=ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(tickets,args.db))
    print(f'RideOps Recovery Desk: http://127.0.0.1:{args.port}')
    print(f'Source: {args.csv} ({len(tickets)} tickets). Local activity DB: {args.db}')
    try:srv.serve_forever()
    except KeyboardInterrupt:pass
    finally:srv.server_close()

if __name__=='__main__':main()
