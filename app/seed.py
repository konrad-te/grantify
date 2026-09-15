"""Provide twelve fictional grants for a new, empty demo database."""

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Grant


def seed_grants(session: Session) -> None:
    """Insert and commit twelve fictional grants only when the table is empty.

    An existing row makes this a no-op, so restarting does not duplicate
    or overwrite data. Deadlines are relative to the first seeding date;
    stored dates stay fixed. All programmes and source links are fictional."""
    if session.scalar(select(Grant.id).limit(1)) is not None:
        return
    # Relative dates keep a fresh installation useful. Stored dates do not roll forward.
    today = date.today()
    samples = [
        ("Factory Energy Upgrade", "Efficient motors, heat recovery and insulation for SME factories.",
         ["Poland"], ["SME"], ["manufacturing"], ["energy_efficiency"], 20000, 300000, 180),
        ("Clean Production Fund", "Cleaner industrial processes, reduced energy use and lower waste.",
         ["Poland", "Germany", "Czechia"], ["SME", "large"], ["manufacturing"],
         ["energy_efficiency", "circular_economy"], 100000, 1000000, 240),
        ("SME Rooftop Solar", "On-site solar generation and battery storage for small businesses.",
         ["Poland"], ["SME"], ["all"], ["renewable_energy"], 30000, 250000, 120),
        ("Digital Workshop", "Factory automation, sensors and production planning software.",
         ["Poland", "Czechia"], ["SME"], ["manufacturing"], ["digitalization"], 10000, 200000, 150),
        ("Circular Materials Pilot", "Reuse of production by-products and recycling process trials.",
         ["Poland", "Germany"], ["SME"], ["manufacturing", "waste_management"],
         ["circular_economy"], 50000, 400000, 210),
        ("Software Research Starter", "Prototype development and experimental software research.",
         ["Poland"], ["SME"], ["software"], ["research_and_development"], 25000, 200000, 90),
        ("Farm Water Efficiency", "Precision irrigation and water-saving equipment for farms.",
         ["Poland", "Czechia"], ["SME"], ["agriculture"], ["water_efficiency"], 10000, 180000, 160),
        ("German Factory Retrofit", "Energy-saving equipment for German manufacturers.",
         ["Germany"], ["SME"], ["manufacturing"], ["energy_efficiency"], 50000, 500000, 200),
        ("Large Industry Decarbonisation", "Industrial heat upgrades for large enterprises.",
         ["Poland"], ["large"], ["manufacturing"], ["energy_efficiency"], 100000, 2000000, 270),
        ("Local Energy Microgrant", "Small energy audits and minor lighting improvements.",
         ["Poland"], ["SME"], ["all"], ["energy_efficiency"], 1000, 15000, 60),
        ("Industrial Transformation", "Major industrial electrification and plant redesign.",
         ["Poland", "Germany"], ["SME", "large"], ["manufacturing"],
         ["energy_efficiency"], 500000, 5000000, 300),
        ("Previous Green Factory Round", "A closed demonstration round for factory energy upgrades.",
         ["Poland"], ["SME"], ["manufacturing"], ["energy_efficiency"], 20000, 300000, -30),
    ]
    for grant_id, sample in enumerate(samples, start=1):
        title, description, countries, sizes, industries, projects, minimum, maximum, days = sample
        session.add(Grant(
            id=grant_id, title=title, description=description, countries=countries,
            company_sizes=sizes, industries=industries, project_types=projects,
            minimum_funding=minimum, maximum_funding=maximum,
            deadline=today + timedelta(days=days),
            source_url=f"https://example.com/mock-grants/{grant_id}",
        ))
    session.commit()
