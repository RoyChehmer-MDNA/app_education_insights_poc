"""Deterministic local agents; no model or external service calls."""
import csv
import io
import json
import math
from pathlib import Path
from .data import allowed_ids, get_attendance, summary


def import_csv(raw, user):
    try:
        reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
        required = {'school_id', 'school', 'grade', 'previous', 'current', 'students'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('CSV requires: ' + ', '.join(sorted(required)))
        rows, seen = [], set()
        for record in reader:
            if len(rows) >= 1000:
                raise ValueError('Maximum 1000 rows')
            row = {k: (record.get(k) or '').strip() for k in required}
            if row['school_id'] not in allowed_ids(user):
                raise PermissionError('Unauthorized school')
            if row['school_id'] in seen:
                raise ValueError('One row per school is required')
            seen.add(row['school_id'])
            if not row['school'] or not row['grade'] or len(row['school']) > 120 or len(row['grade']) > 30:
                raise ValueError('Invalid school or grade')
            for key in ('previous', 'current'):
                row[key] = float(row[key])
                if not math.isfinite(row[key]) or not 0 <= row[key] <= 100:
                    raise ValueError('Attendance must be between 0 and 100')
            row['students'] = int(row['students'])
            if not 0 < row['students'] <= 100000:
                raise ValueError('Invalid student count')
            rows.append(row)
        if not rows:
            raise ValueError('CSV is empty')
        return rows
    except (UnicodeError, csv.Error, TypeError) as exc:
        raise ValueError('Invalid UTF-8 CSV') from exc


class Orchestrator:
    def __init__(self, store, sources_path):
        self.store, self.sources_path = store, Path(sources_path)

    def rows(self, user):
        imported = self.store.get(user, 'attendance')
        rows = imported if imported is not None else get_attendance(user)
        return [r for r in rows if r['school_id'] in allowed_ids(user)]

    def run(self, question, user, conversation, school_id=None):
        if not isinstance(question, str) or not 1 <= len(question.strip()) <= 800:
            raise ValueError('השאלה חייבת להכיל 1–800 תווים')
        context = self.store.get(user, 'context:' + conversation, {})
        school_id = school_id or context.get('school_id')
        if school_id and school_id not in allowed_ids(user):
            raise PermissionError('Unauthorized school')
        rows = self.rows(user)
        if school_id:
            rows = [r for r in rows if r['school_id'] == school_id]
        if not rows:
            raise ValueError('אין נתונים בטווח שנבחר')
        stats = summary(rows)
        largest = max(rows, key=lambda r: r['previous'] - r['current'])
        delta = round(largest['current'] - largest['previous'], 1)
        finding = f"ממוצע הנוכחות: {stats['average']}%. שינוי ממוצע: {stats['decline']} נקודות אחוז. השינוי הנמוך ביותר: {largest['school']}, {delta:+} נקודות אחוז. אין בנתונים הסבר לסיבות לשינוי."
        sources = json.loads(self.sources_path.read_text(encoding='utf-8'))
        approved = [s for s in sources if s.get('approved') is True and all(isinstance(s.get(k), str) and s[k].strip() for k in ('id', 'title', 'recommendation'))]
        advice = '\n'.join(f"{s['recommendation']} (מקור: {s['title']}, {s['id']})" for s in approved)
        if not advice:
            advice = 'לא הוגדרו מקורות מאושרים להמלצות. נדרש אישור מקור לפני מתן המלצה.'
        source = 'uploaded_csv' if self.store.get(user, 'attendance') is not None else 'demo_data'
        result = dict(answer=f'ממצא: {finding}\n\nהמלצה: {advice}', mode='local', data_mode=source,
                      source=source, facts=stats, rows=rows, conversation_id=conversation,
                      context={'school_id': school_id}, advice_sources=[{'id': s['id'], 'title': s['title']} for s in approved],
                      trace=['context', 'authorized_data', 'insight_agent', 'advice_agent', 'persistence'],
                      limitations=['ניתוח דטרמיניסטי מקומי; השאלה נשמרת אך אינה מפוענחת במודל שפה'],
                      suggested_action={'type': 'qlik.selection.proposal', 'status': 'not_executed', 'field': 'school_id', 'values': [largest['school_id']], 'description': 'סינון עתידי לפי בית ספר'})
        self.store.save(user, conversation, question.strip(), result, rows)
        self.store.put(user, 'context:' + conversation, {'school_id': school_id})
        return result
