"""Source-backed pilot catalogue and conservative topic shortlisting.

The legacy SQLite demo is deliberately not read or overwritten here. Published
programme summaries are not a complete machine-readable eligibility rulebook.
"""
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.structured import ACTIVITIES

CATALOGUE_PATH = Path(__file__).parent / 'data' / 'programmes.json'
DEMO_CATALOGUE_PATH = Path(__file__).parent / 'data' / 'demo-europe-2026-10-04.json'
DEMO_DATE = date(2026, 10, 4)


def current_date():
    return datetime.now(ZoneInfo('Europe/Warsaw')).date()


class Programme(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    id: str
    title: str
    source_url: str
    countries: list[str] = Field(min_length=1)
    country_note: str
    country_source_url: str
    schedule_source_url: str
    activities: list[str] = Field(min_length=1)
    description: str
    opens_on: date | None
    closes_on: date | None
    instrument: str
    max_award: Decimal | None = Field(default=None, gt=0)
    currency: Literal['PLN', 'EUR']
    checks: list[str] = Field(min_length=1)
    reviewed_on: date
    cancelled: bool = False

    @model_validator(mode='after')
    def check_source_and_dates(self):
        for source in (self.source_url, self.country_source_url, self.schedule_source_url):
            url = urlparse(source)
            if url.scheme != 'https' or url.hostname not in {
                'eic.ec.europa.eu', 'cinea.ec.europa.eu', 'ec.europa.eu',
                'www.eurekanetwork.org', 'eurekanetwork.org'
            } or url.username or url.password:
                raise ValueError('Expected an official HTTPS programme source')
        if len(set(self.countries)) != len(self.countries):
            raise ValueError('Duplicate countries')
        if not set(self.activities) <= ACTIVITIES.keys():
            raise ValueError('Unknown activity tag')
        if self.opens_on and self.closes_on and self.opens_on > self.closes_on:
            raise ValueError('Invalid application window')
        return self


def load_catalogue(path=None):
    data = json.loads((path or CATALOGUE_PATH).read_text(encoding='utf-8'))
    programmes = [Programme.model_validate(row) for row in data['programmes']]
    if len({p.id for p in programmes}) != len(programmes):
        raise ValueError('Duplicate programme IDs')
    if len({p.source_url for p in programmes}) != len(programmes):
        raise ValueError('Duplicate programme sources')
    return programmes


def load_demo_catalogue():
    return load_catalogue(DEMO_CATALOGUE_PATH)


def availability(programme, today):
    if programme.cancelled:
        return 'cancelled', 'Published call cancelled'
    if programme.closes_on and programme.closes_on < today:
        return 'closed', 'Published call closed'
    # Do not silently advertise an old snapshot as current availability.
    if (today - programme.reviewed_on).days > 30 or today < programme.reviewed_on:
        return 'unknown', 'Schedule needs rechecking'
    if programme.opens_on and today < programme.opens_on:
        return 'upcoming', 'Upcoming published call'
    if programme.opens_on and programme.closes_on:
        return 'window', 'Within published window — confirm recruitment'
    return 'unknown', 'Availability not verified'


def shortlist(project, programmes, today=None):
    today = today or current_date()
    groups = {'candidates': [], 'upcoming': [], 'archive': [], 'excluded': []}
    for p in programmes:
        status, label = availability(p, today)
        matched = [key for key in project.activities if key in p.activities]
        reasons = []
        if project.company_size != 'SME':
            reasons.append('Outside this pilot’s scope: startups and SMEs. This is not a programme eligibility decision.')
        if project.country.casefold() not in {c.casefold() for c in p.countries}:
            reasons.append(f'Country not covered by this record’s verified country list: {project.country}. This is a catalogue coverage limit, not a worldwide eligibility decision. Check the country source for other routes or exceptions.')
        if not matched:
            reasons.append('No overlap with the selected activity categories.')
        if p.max_award is None:
            amount_note = 'Funding amount not assessed: no comparable cash-award cap has been recorded.'
        elif project.currency != p.currency:
            amount_note = f'Funding amount not assessed: the published cap is in {p.currency}; no currency conversion is performed.'
        elif project.requested_funding > p.max_award:
            reasons.append(f'Request exceeds the published maximum of {p.currency} {p.max_award:,.0f}.')
            amount_note = reasons[-1]
        else:
            amount_note = 'Request does not exceed the recorded cap. Eligible costs, minimum amounts and co-funding are still unverified.'
        questions = [p.country_note, *p.checks]
        remaining = [ACTIVITIES[a] for a in project.activities if a not in p.activities]
        if remaining:
            questions.append('Other selected activities are not covered by these topic tags: ' + '; '.join(remaining) + '.')
        questions.append('Sector exclusions, eligible costs, aid limits and required own contribution need review in the official documentation.')
        row = {'programme': p, 'availability': status, 'status': label,
               'matched': [ACTIVITIES[a] for a in matched], 'questions': questions,
               'amount_note': amount_note, 'reasons': reasons}
        group = ('excluded' if reasons else 'archive' if status in {'closed', 'cancelled'}
                 else 'upcoming' if status == 'upcoming' else 'candidates')
        groups[group].append(row)
    for rows in groups.values():
        rows.sort(key=lambda r: (-len(r['matched']), r['programme'].title.casefold(), r['programme'].id))
    return groups
