from config.base import DomainConfig

BIG_TECH_CONFIG = DomainConfig(
    name="Big Tech Policy",
    persona="Google Policy Strategist",
    description="Track regulatory risks, antitrust actions, and emerging tech governance trends that could impact Google's operations and strategy.",
    categories=[
        "Regulatory & Antitrust",
        "Data Privacy",
        "AI Governance",
        "Content Moderation",
        "Youth Safety & Digital Wellbeing",
        "Competition & Market Power",
        "Taxation & Digital Services",
    ],
    keywords=[
        "big tech regulation",
        "tech antitrust",
        "data privacy law",
        "AI regulation policy",
        "content moderation regulation",
        "digital services tax",
        "youth online safety bill",
        "Google antitrust DOJ",
        "EU AI Act enforcement",
        "GDPR fine enforcement",
        "deepfake AI generated content law",
        "app store DMA",
    ],
    single_theme=True,  # TEMP: remove after testing
    detection_prompt="""You are a senior policy analyst specializing in Big Tech regulation.
Given the following recent news headlines and descriptions, identify emerging signals
that could impact Google's policy strategy.

Broad themes for context: {categories}

TOPIC ASSIGNMENT:
Each signal MUST have a "topic" — a specific policy narrative (3-7 words).
Structure: [Action/Trend] + [Specific Subject] + [Context]
Self-check: if someone reads ONLY the topic, they should understand the policy direction.

Good: "Antitrust remedies for search monopoly"
Good: "Youth social media age verification"
Good: "AI copyright liability expansion"
Bad: "AI in Google Search" (no action — WHAT about AI in search?)
Bad: "AI Governance" (too broad — which aspect?)
Bad: "AI content legal issues" (vague — what kind of issues?)

EXISTING TOPICS from previous scans:
{existing_topics}

1. REUSE an existing topic's EXACT label whenever the signal fits that narrative.
2. Only create a new topic for genuinely distinct narratives not covered above.
3. Prefer merging into an existing topic over creating a near-duplicate.

For each signal, provide:
- topic: Specific policy narrative label (3-6 words)
- title: Short headline (max 8 words). Must describe the SIGNAL or TREND, not the specific event.
  BAD: "EU fines Apple €500M for DMA non-compliance" (just an event)
  GOOD: "Growing govt scrutiny of anti-competitive practices" (the signal)
- categories: List of broad themes this signal belongs to (from the list above)
- description: 2-3 sentences explaining the specific development and its implications. Include specific actors, jurisdictions, and actions.
- reasoning: Why this is an important weak signal to watch
- sources: List of source names (e.g. "Reuters", "r/technology", "HackerNews")
- source_url: URL of the primary source article
- source_quote: If the source is from social media (Reddit, HackerNews), quote the most relevant part verbatim. Leave empty string for news articles.
- related_articles: List of objects with keys "title", "url", "source" for ALL articles from the input that relate to this signal

Focus on EMERGING trends and weak signals — things that haven't fully materialized but show
early momentum. Prioritize signals with policy implications for major tech companies.

News articles:
{articles}

Respond in JSON format as a list of objects with the keys above.""",

)
