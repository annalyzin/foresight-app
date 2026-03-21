from config.base import DomainConfig

SG_MANPOWER_CONFIG = DomainConfig(
    name="Singapore Manpower",
    persona="MOM Policy Officer",
    description="Track emerging workforce trends, labour market shifts, and policy signals relevant to Singapore's manpower planning and regulation.",
    categories=[
        "Foreign Workforce Policy",
        "Skills & Training",
        "Gig Economy & Platform Work",
        "Aging Workforce & Retirement",
        "Automation & Job Displacement",
        "Wage Policy & Progressive Wages",
        "Workplace Safety & Health",
    ],
    feeds=[
        # Google News RSS — broad
        "https://news.google.com/rss/search?q=Singapore+workforce+policy&hl=en&gl=SG&ceid=SG:en",
        "https://news.google.com/rss/search?q=Singapore+foreign+workers&hl=en&gl=SG&ceid=SG:en",
        "https://news.google.com/rss/search?q=Singapore+gig+economy&hl=en&gl=SG&ceid=SG:en",
        "https://news.google.com/rss/search?q=Singapore+wages+employment&hl=en&gl=SG&ceid=SG:en",
        "https://news.google.com/rss/search?q=Singapore+automation+jobs&hl=en&gl=SG&ceid=SG:en",
        "https://news.google.com/rss/search?q=Singapore+skills+training&hl=en&gl=SG&ceid=SG:en",
        # Google News RSS — category-specific
        "https://news.google.com/rss/search?q=Singapore+employment+pass+COMPASS&hl=en&gl=SG&ceid=SG:en",
        "https://news.google.com/rss/search?q=Singapore+progressive+wage+model&hl=en&gl=SG&ceid=SG:en",
        "https://news.google.com/rss/search?q=Singapore+workplace+safety+construction&hl=en&gl=SG&ceid=SG:en",
        "https://news.google.com/rss/search?q=Singapore+retirement+age+CPF&hl=en&gl=SG&ceid=SG:en",
        "https://news.google.com/rss/search?q=Singapore+SkillsFuture+reskilling&hl=en&gl=SG&ceid=SG:en",
        "https://news.google.com/rss/search?q=Singapore+platform+workers+Grab+delivery&hl=en&gl=SG&ceid=SG:en",
        "https://news.google.com/rss/search?q=Singapore+AI+jobs+displacement&hl=en&gl=SG&ceid=SG:en",
        "https://news.google.com/rss/search?q=Singapore+MOM+manpower+policy&hl=en&gl=SG&ceid=SG:en",
        # CNA
        "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml&category=6511",
        # Reddit
        "https://www.reddit.com/r/singapore/.rss",
        "https://www.reddit.com/r/askSingapore/.rss",
        # HackerNews
        "https://hnrss.org/newest?q=Singapore+workforce",
        "https://hnrss.org/newest?q=gig+economy+regulation",
        "https://hnrss.org/newest?q=Singapore+AI+jobs",
        # ILO
        "https://www.ilo.org/feed/news/en",
    ],
    keywords=[
        "Singapore workforce policy",
        "Singapore foreign workers",
        "Singapore gig economy",
        "Singapore wages employment",
        "Singapore automation jobs",
        "Singapore skills training",
        "Singapore employment pass COMPASS",
        "Singapore progressive wage model",
        "Singapore workplace safety",
        "Singapore retirement age CPF",
        "Singapore platform workers",
        "Singapore AI jobs displacement",
    ],
    detection_prompt="""You are a senior policy analyst at Singapore's Ministry of Manpower.
Given the following recent news headlines and descriptions, identify emerging signals
that could affect Singapore's manpower policies.

Broad themes for context: {categories}

TOPIC ASSIGNMENT:
Each signal MUST have a "topic" — a specific policy narrative (3-6 words).
Good: "Platform worker CPF protections", "Foreign workforce COMPASS tightening"
Bad: "Workforce Policy" (too broad), "Jobs" (too vague)

EXISTING TOPICS from previous scans:
{existing_topics}

If a signal relates to an existing topic, REUSE that EXACT label.
Only create a new topic for genuinely distinct narratives.

For each signal, provide:
- topic: Specific policy narrative label (3-6 words)
- title: Short headline (max 8 words). Must describe the SIGNAL or TREND, not the specific event.
  BAD: "MOM tightens COMPASS bonus point criteria" (just an event)
  GOOD: "Accelerating foreign workforce restrictions" (the signal)
- categories: List of broad themes this signal belongs to (from the list above)
- description: 2-3 sentences explaining the specific development and its implications. Include specific actors, policies, and numbers where available.
- reasoning: Why this matters for Singapore's workforce planning
- sources: List of source names (e.g. "Channel NewsAsia", "r/singapore", "The Straits Times")
- source_url: URL of the primary source article
- source_quote: If the source is from social media (Reddit, HackerNews), quote the most relevant part verbatim. Leave empty string for news articles.
- related_articles: List of objects with keys "title", "url", "source" for ALL articles from the input that relate to this signal

Focus on EMERGING trends and weak signals — early indicators of shifts in labour markets,
workforce composition, or employment patterns that may require policy response.

News articles:
{articles}

Respond in JSON format as a list of objects with the keys above.""",

)
