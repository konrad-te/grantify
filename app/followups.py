"""Programme-specific evidence questions for narrowing a funding lead.

The answers remain self-reported. They help a user decide whether a programme
deserves further investigation; they never establish eligibility.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class FollowUp:
    key: str
    prompt: str
    why: str
    example: str
    supported: str
    missing: str


@dataclass(frozen=True)
class AssessmentGuide:
    remaining: tuple[str, ...]
    next_action: str


QUESTIONS = {
    "eic-accelerator": (
        FollowUp(
            "tested",
            "Where has the technology been tested, and what did the test prove?",
            "EIC expects evidence that the technology works in a relevant setting.",
            "Example: three forest sites, 20 controlled fires, detection times and false-alarm counts.",
            "You described testing in a real-world setting.",
            "Real-world test results are still missing.",
        ),
        FollowUp(
            "advantage",
            "What measurable result makes it better than existing solutions?",
            "EIC looks for a significant technical advance, not just a new app or ordinary improvement.",
            "Compare with ordinary cameras, fire-watch towers or satellite alerts under the same conditions.",
            "You described a measurable advantage over an existing solution.",
            "A measurable advantage over existing solutions is still missing.",
        ),
        FollowUp(
            "market",
            "What evidence shows that customers want it?",
            "EIC assesses customer demand, the market opportunity and the plan to grow.",
            "Example: signed agreements for two paid municipal pilots, including dates and price.",
            "You described evidence of customer interest.",
            "Customer evidence is still missing.",
        ),
        FollowUp(
            "delivery", "Who will build, operate and sell the product?",
            "A useful idea needs a team and a realistic delivery plan.",
            "Describe the AI, hardware, manufacturing and sales roles, plus safety checks and milestones.",
            "You described a delivery team and plan.", "The delivery team and plan are unclear.",
        ),
        FollowUp(
            "budget", "What will the money pay for, and how will you cover the rest?",
            "The programme needs a credible budget and financing plan.",
            "Break down development, field tests, production and sales costs; say where your contribution comes from.",
            "You described planned spending.", "The spending and financing plan is unclear.",
        ),
    ),
    "eic-pathfinder-challenges": (
        FollowUp(
            "challenge",
            "Which named 2026 Pathfinder Challenge does the project address, and how?",
            "A broad research topic is not enough; the project must fit a specific challenge guide.",
            "Name the challenge and connect your proposed research to its stated objective.",
            "You connected the research to a named Pathfinder Challenge.",
            "A direct fit with a named 2026 Pathfinder Challenge is still missing.",
        ),
        FollowUp(
            "early_research",
            "What radical technology are you trying to create, and what is the main technical risk?",
            "Pathfinder supports early, high-risk science-to-technology work.",
            "Describe the new technology, the experiment and the reason it may fail.",
            "You described an early breakthrough idea and its technical risk.",
            "The breakthrough idea and high-risk research question are still unclear.",
        ),
    ),
    "eureka-network": (
        FollowUp(
            "international_partner",
            "Who is your independent partner in another Eureka country, and where are they based?",
            "A Network Project needs independent organisations in at least two participating countries.",
            "Give the organisation name, country and the work it would perform.",
            "You described an international project partner.",
            "The required international partner is still missing.",
        ),
        FollowUp(
            "joint_research",
            "What will each partner research or develop?",
            "The programme supports a genuinely shared research and development project.",
            "Explain your work package, your partner's work package and what you will create together.",
            "You described shared research or development work.",
            "The joint research and development plan is still unclear.",
        ),
        FollowUp(
            "national_funding",
            "Which national funding body did you check, and what did it confirm?",
            "Participation in a Eureka project does not automatically provide national funding.",
            "Name the funding body, the route checked and any response or published condition.",
            "You described a national funding route.",
            "Funding for your part of the project is still unconfirmed.",
        ),
    ),
    "innowwide": (
        FollowUp(
            "company_age",
            "When was the company legally established?",
            "The 2026 call requires the applicant company to be at least two years old by its deadline.",
            "Give the legal registration date, not the date the idea or team started.",
            "You provided a company establishment date to compare with the age rule.",
            "The company establishment date is still missing.",
        ),
        FollowUp(
            "local_partner",
            "Who will perform paid work in the target country?",
            "The project needs an independent local subcontractor in the overseas target country.",
            "Give the organisation, country, independence from your company and planned work.",
            "You described a possible local subcontractor.",
            "The required independent local subcontractor is still missing.",
        ),
        FollowUp(
            "eligible_costs",
            "Which planned costs make up at least EUR 86,000 of eligible project spending?",
            "The total budget is insufficient if part of it falls outside the eligible-cost rules.",
            "List the main staff, travel, subcontracting or other costs and their approximate amounts.",
            "You provided a cost breakdown to compare with the minimum eligible-cost rule.",
            "An eligible-cost breakdown of at least EUR 86,000 is still missing.",
        ),
    ),
}


GUIDES = {
    "eic-accelerator": AssessmentGuide(
        remaining=(
            "Whether a current EIC Accelerator submission route is open for this project.",
            "Whether reviewers accept the stated testing, technical advantage and customer evidence.",
            "The correct funding component, eligible costs, co-funding and amount limits.",
        ),
        next_action=(
            "Prepare a one-page evidence pack with the test results, comparison with current "
            "solutions and customer proof. Then compare it with the current EIC Accelerator rules."
        ),
    ),
    "eic-pathfinder-challenges": AssessmentGuide(
        remaining=(
            "Whether the project satisfies every condition in the selected Challenge guide.",
            "Whether the research stage, team and consortium structure meet the call rules.",
            "The current deadline, eligible costs and funding conditions.",
        ),
        next_action=(
            "Open the selected Challenge guide and map each expected outcome to a concrete "
            "experiment, partner and piece of evidence in your project."
        ),
    ),
    "eureka-network": AssessmentGuide(
        remaining=(
            "Whether both countries are participating in the intended call.",
            "Whether each national funding body accepts its applicant and project costs.",
            "The application dates and any country-specific conditions.",
        ),
        next_action=(
            "Ask both national funding bodies to confirm the intended partners, call route and "
            "eligible costs before developing the joint application."
        ),
    ),
    "innowwide": AssessmentGuide(
        remaining=(
            "Whether the applicant and target country satisfy every call condition.",
            "Whether the proposed subcontractor is sufficiently independent.",
            "Whether the detailed budget contains at least EUR 86,000 of eligible costs.",
        ),
        next_action=(
            "Put the registration date, local subcontractor agreement and itemised eligible-cost "
            "budget beside the current Innowwide call rules and resolve any mismatch."
        ),
    ),
}


def assess_answers(programme_id, questions, answers):
    """Turn self-reported evidence into useful next steps without certifying it."""
    supplied = [q for q in questions if answers[q.key]["status"] == "supplied"]
    unresolved = [q for q in questions if answers[q.key]["status"] == "unknown"]
    guide = GUIDES[programme_id]
    if unresolved:
        heading = "Not enough evidence yet"
        summary = (
            f"You provided useful detail for {len(supplied)} of {len(questions)} key areas. "
            "The missing evidence could change whether this programme is worth pursuing."
        )
    else:
        heading = "Promising lead — worth investigating"
        summary = (
            "Your answers address the first project-level questions. Gratify has not verified "
            "the evidence, and the programme rules below can still prevent an application."
        )
    return {
        "heading": heading,
        "summary": summary,
        "supplied": [(q, answers[q.key]["evidence"]) for q in supplied],
        "unresolved": unresolved,
        "remaining": guide.remaining,
        "next_action": guide.next_action,
    }
