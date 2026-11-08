# Recall a past session («в прошлой сессии обсуждали X»)

Use when the user refers to an earlier conversation and no session-search / chat-history tool is in the toolset. The session DB is the source of truth.

## Procedure

1. In `execute_code` (the `sqlite3` CLI may be absent — Python's module works):
   ```python
   import sqlite3, os, time, datetime
   db = sqlite3.connect(os.path.expanduser('~/.hermes/state.db'))
   q = """select s.id, s.started_at, s.title, count(*) from sessions s
          join messages m on m.session_id=s.id
          where m.role in ('user','assistant') and lower(m.content) like ?
            and s.started_at > ? group by s.id order by s.started_at desc limit 15"""
   for r in db.execute(q, ('%налог%', time.time()-30*86400)):
       print(r[0], datetime.datetime.fromtimestamp(r[1]+3*3600, datetime.UTC), r[2], r[3])
   ```
   Search several keyword stems (Russian morphology: `налог`, not `налоги`). `started_at` is UTC epoch — add 3 h for MSK.
2. Session titles are auto-generated in English and often unrelated to the topic (a tax talk titled «Describe contents of attached images») — rank by hit count + recency, not by title.
3. Read the chosen session: `select role, content, timestamp from messages where session_id=? and role in ('user','assistant') and content!='' order by id`.
4. Answer with: when it was (MSK), where it stopped, open question — then continue the actual task. Re-verify any factual claims from that session before repeating them; correct them explicitly if they were wrong.

## Pitfalls

- A garbled voice transcript («three sessions discussed on the clock») — ask one short clarifying question, then query the DB as soon as the user gives a topic; don't make them repeat the content.
- The current session also matches the keyword — skip it (newest id).
