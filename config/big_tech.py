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
    feeds=[
        # Google News RSS — broad
        "https://news.google.com/rss/search?q=big+tech+regulation&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=tech+antitrust&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=data+privacy+law&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=youth+online+safety+bill&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=digital+services+tax&hl=en&gl=US&ceid=US:en",
        # Google News RSS — category-specific
        "https://news.google.com/rss/search?q=AI+regulation+policy+governance&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=AI+model+ban+safety+enforcement&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=content+moderation+regulation&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=deepfake+AI+generated+content+law&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Google+antitrust+DOJ&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=Apple+Google+app+store+DMA&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=GDPR+fine+enforcement&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=children+social+media+ban+age+verification&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=EU+AI+Act+enforcement&hl=en&gl=US&ceid=US:en",
        "https://news.google.com/rss/search?q=tech+platform+competition+interoperability&hl=en&gl=US&ceid=US:en",
        # Reuters
        "https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best&best-sectors=tech",
        # Reddit
        "https://www.reddit.com/r/technology/.rss",
        "https://www.reddit.com/r/privacy/.rss",
        "https://www.reddit.com/r/technews/.rss",
        # HackerNews
        "https://hnrss.org/newest?q=big+tech+regulation",
        "https://hnrss.org/newest?q=AI+governance",
        "https://hnrss.org/newest?q=AI+ban",
        "https://hnrss.org/newest?q=antitrust+Google",
        "https://hnrss.org/newest?q=content+moderation",
        "https://hnrss.org/newest?q=data+privacy+GDPR",
        # Think tanks & orgs
        "https://www.eff.org/rss/updates.xml",
        # arXiv
        "https://rss.arxiv.org/rss/cs.CY",
    ],
    detection_prompt="""You are a senior policy analyst specializing in Big Tech regulation.
Given the following recent news headlines and descriptions, identify emerging signals
that could impact Google's policy strategy.

Broad themes for context: {categories}

TOPIC ASSIGNMENT:
Each signal MUST have a "topic" — a specific policy narrative (3-6 words).
Good: "Youth social media bans", "Google Search antitrust remedies"
Bad: "AI Governance" (too broad), "Regulation" (too vague)

EXISTING TOPICS from previous scans:
{existing_topics}

If a signal relates to an existing topic, REUSE that EXACT label.
Only create a new topic for genuinely distinct narratives.

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
