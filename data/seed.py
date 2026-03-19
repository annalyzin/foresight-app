"""Generate topic-based seed data for demo charts."""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import List

from data.models import Signal, SourceArticle
from data.store import load_signals, save_signals
from engine.scorer import score_signal

# Each entry: (topic, title, categories, description, month_offset, source_name, source_url, source_quote, related_articles)
# related_articles: list of (title, url, source) tuples
# Scores are computed automatically from related_articles using the article-count formula.

_BIG_TECH_SEEDS = [
    # ── Google Search antitrust remedies (8 signals) ──
    ("Google Search antitrust remedies",
     "Mounting judicial challenge to search dominance", ["Regulatory & Antitrust"],
     "Federal judge rules Google maintained illegal monopoly in search through exclusive default deals worth billions, setting stage for potential structural remedies.",
     20, "The New York Times", "https://www.nytimes.com/2024/08/05/technology/google-antitrust-ruling.html", "",
     [("Google loses landmark antitrust case", "https://www.nytimes.com/2024/08/05/technology/google-antitrust-ruling.html", "The New York Times"),
      ("What Google's antitrust loss means for big tech", "https://www.theverge.com/2024/8/google-antitrust-implications", "The Verge")]),

    ("Google Search antitrust remedies",
     "Epic v Google verdict extends antitrust momentum", ["Regulatory & Antitrust", "Competition & Market Power"],
     "Jury finds Google illegally monopolized Android app distribution, ordering Play Store to open to competing app stores — a second major antitrust loss in months.",
     18, "The Verge", "https://www.theverge.com/2024/epic-v-google-verdict", "",
     [("Google loses Epic antitrust trial", "https://www.theverge.com/2024/epic-v-google-verdict", "The Verge"),
      ("Epic v Google: jury finds illegal monopoly", "https://www.reuters.com/technology/epic-google-verdict-2024/", "Reuters"),
      ("What Epic's win means for Android users", "https://arstechnica.com/2024/epic-google-implications/", "Ars Technica")]),

    ("Google Search antitrust remedies",
     "Structural breakup remedies gaining traction", ["Regulatory & Antitrust", "Competition & Market Power"],
     "US Department of Justice files proposed remedy requiring Google to divest Chrome browser, arguing it cements search monopoly through default placement.",
     14, "Reuters", "https://www.reuters.com/technology/doj-proposes-google-chrome-divestiture-2024/", "",
     [("DOJ wants Google to sell Chrome", "https://www.reuters.com/technology/doj-proposes-google-chrome-divestiture-2024/", "Reuters"),
      ("Google Chrome divestiture would reshape browser market", "https://arstechnica.com/2024/chrome-divestiture-analysis/", "Ars Technica")]),

    ("Google Search antitrust remedies",
     "Google ad tech case adds regulatory pressure", ["Regulatory & Antitrust", "Competition & Market Power"],
     "DOJ's second antitrust case targeting Google's ad tech business goes to trial, alleging monopolization of the digital advertising stack from publisher tools to ad exchange.",
     11, "Bloomberg", "https://www.bloomberg.com/news/articles/google-ad-tech-trial-2025", "",
     [("Google ad tech antitrust trial begins", "https://www.bloomberg.com/news/articles/google-ad-tech-trial-2025", "Bloomberg"),
      ("DOJ: Google rigged ad market at publishers' expense", "https://www.washingtonpost.com/technology/2025/google-ad-tech-trial/", "Washington Post")]),

    ("Google Search antitrust remedies",
     "Antitrust remedy phase entering critical stage", ["Regulatory & Antitrust"],
     "Remedy phase of Google antitrust case opens with DOJ seeking structural changes and Google proposing behavioral commitments instead.",
     8, "Bloomberg", "https://www.bloomberg.com/news/articles/google-remedy-trial-2025", "",
     [("Google remedy trial to determine search future", "https://www.bloomberg.com/news/articles/google-remedy-trial-2025", "Bloomberg")]),

    ("Google Search antitrust remedies",
     "Behavioral remedies emerging as compromise path", ["Regulatory & Antitrust", "Competition & Market Power"],
     "As alternative to divestiture, Google proposes choice screen for Android and Chrome users to select default search engine, similar to EU DMA compliance.",
     6, "The Verge", "https://www.theverge.com/2025/google-choice-screen-proposal", "",
     [("Google proposes choice screen to avoid Chrome sale", "https://www.theverge.com/2025/google-choice-screen-proposal", "The Verge")]),

    ("Google Search antitrust remedies",
     "Default deal dependencies exposed in court", ["Regulatory & Antitrust", "Competition & Market Power"],
     "Apple executives testify that losing Google's $20B annual search deal would materially impact services revenue, revealing depth of default agreement dependency.",
     5, "CNBC", "https://www.cnbc.com/2025/apple-google-search-deal-testimony", "",
     [("Apple reveals Google search deal worth $20B", "https://www.cnbc.com/2025/apple-google-search-deal-testimony", "CNBC")]),

    ("Google Search antitrust remedies",
     "Divestiture momentum fading toward softer remedies", ["Regulatory & Antitrust"],
     "Trial judge questions whether Chrome divestiture would effectively restore competition, suggesting behavioral remedies with monitoring may suffice.",
     3, "Washington Post", "https://www.washingtonpost.com/technology/2025/judge-google-remedy-skepticism/", "",
     [("Judge leans away from Google Chrome breakup", "https://www.washingtonpost.com/technology/2025/judge-google-remedy-skepticism/", "Washington Post")]),

    # ── Youth social media bans (8 signals) ──
    ("Youth social media bans",
     "Bipartisan momentum for youth platform controls", ["Youth Safety & Digital Wellbeing", "Content Moderation"],
     "US Senate passes KOSA with bipartisan 91-3 vote, imposing duty of care on platforms to prevent harm to minors. House action still pending.",
     22, "The Washington Post", "https://www.washingtonpost.com/technology/2024/07/30/kosa-senate-vote/", "",
     [("Senate overwhelmingly passes kids' online safety bill", "https://www.washingtonpost.com/technology/2024/07/30/kosa-senate-vote/", "The Washington Post"),
      ("KOSA passes Senate with rare bipartisan support", "https://www.nytimes.com/2024/07/kosa-senate/", "The New York Times")]),

    ("Youth social media bans",
     "Anxious Generation fueling parental advocacy wave", ["Youth Safety & Digital Wellbeing"],
     "Jonathan Haidt's 'The Anxious Generation' becomes bestseller, catalyzing parent advocacy groups demanding legislative action on youth social media access across US and UK.",
     18, "The Atlantic", "https://www.theatlantic.com/technology/2024/haidt-anxious-generation-impact/", "",
     [("Haidt's book sparks youth social media backlash", "https://www.theatlantic.com/technology/2024/haidt-anxious-generation-impact/", "The Atlantic"),
      ("Parents mobilize against social media for kids", "https://www.nytimes.com/2024/parent-advocacy-social-media/", "The New York Times"),
      ("The Anxious Generation becomes rallying cry", "https://www.theguardian.com/books/2024/haidt-anxious-generation/", "The Guardian")]),

    ("Youth social media bans",
     "Florida signs strict youth social media law", ["Youth Safety & Digital Wellbeing", "Regulatory & Antitrust"],
     "Florida Governor signs HB 3 banning social media accounts for children under 14 and requiring parental consent for 14-15 year olds, with platform verification mandates.",
     14, "NBC News", "https://www.nbcnews.com/tech/florida-social-media-ban-minors-2024", "",
     [("Florida bans social media for under-14s", "https://www.nbcnews.com/tech/florida-social-media-ban-minors-2024", "NBC News"),
      ("Florida's youth social media ban faces legal challenge", "https://www.washingtonpost.com/technology/2024/florida-youth-ban/", "Washington Post")]),

    ("Youth social media bans",
     "Age-based platform bans going global", ["Youth Safety & Digital Wellbeing"],
     "Australia passes world's first social media age ban, prohibiting platforms from allowing users under 16. Tech companies face fines up to AUD 50M for non-compliance.",
     10, "BBC News", "https://www.bbc.com/news/articles/australia-social-media-ban-2024", "",
     [("Australia passes social media ban for under-16s", "https://www.bbc.com/news/articles/australia-social-media-ban-2024", "BBC News"),
      ("How Australia's social media ban will work", "https://www.theguardian.com/australia-news/2024/social-media-ban-explained", "The Guardian")]),

    ("Youth social media bans",
     "Coordinated state-level youth safety litigation", ["Youth Safety & Digital Wellbeing", "Regulatory & Antitrust"],
     "Fourteen US states file coordinated lawsuits against Meta for addictive design features targeting children, seeking age verification mandates.",
     8, "NBC News", "https://www.nbcnews.com/tech/states-sue-meta-children-2025", "",
     [("States sue Meta over children's social media harm", "https://www.nbcnews.com/tech/states-sue-meta-children-2025", "NBC News")]),

    ("Youth social media bans",
     "UK Online Safety Act enforcement begins", ["Youth Safety & Digital Wellbeing", "Content Moderation"],
     "Ofcom begins enforcing UK Online Safety Act with mandatory age verification and content filtering requirements for platforms, issuing first compliance notices to TikTok and Snap.",
     6, "BBC News", "https://www.bbc.com/news/technology/online-safety-act-enforcement-2025", "",
     [("Ofcom starts enforcing Online Safety Act", "https://www.bbc.com/news/technology/online-safety-act-enforcement-2025", "BBC News"),
      ("TikTok and Snap get first Online Safety Act notices", "https://www.theguardian.com/technology/2025/online-safety-act-enforcement/", "The Guardian")]),

    ("Youth social media bans",
     "Age verification mandate nearing federal law", ["Youth Safety & Digital Wellbeing"],
     "House Energy and Commerce Committee advances bill requiring age verification for social media, combining KOSA provisions with ID-based verification mandate.",
     4, "Politico", "https://www.politico.com/news/2025/age-verification-bill-committee", "",
     [("Age verification bill advances in House", "https://www.politico.com/news/2025/age-verification-bill-committee", "Politico")]),

    ("Youth social media bans",
     "Australia begins enforcing social media age ban", ["Youth Safety & Digital Wellbeing"],
     "Australia's eSafety Commissioner begins enforcement of under-16 social media ban, requiring platforms to implement age assurance technology. Meta and TikTok submit compliance plans.",
     2, "The Guardian", "https://www.theguardian.com/australia-news/2025/social-media-ban-enforcement/", "",
     [("Australia starts enforcing youth social media ban", "https://www.theguardian.com/australia-news/2025/social-media-ban-enforcement/", "The Guardian"),
      ("Meta submits Australia age ban compliance plan", "https://www.smh.com.au/technology/meta-age-ban-compliance-2025", "Sydney Morning Herald")]),

    # ── EU AI Act enforcement (8 signals) ──
    ("EU AI Act enforcement",
     "Comprehensive AI regulation becoming law", ["AI Governance", "Regulatory & Antitrust"],
     "EU Council gives final approval to AI Act, the world's first comprehensive AI law. Two-year implementation timeline begins with prohibited practices banned first.",
     24, "Reuters", "https://www.reuters.com/technology/eu-ai-act-adopted-2024/", "",
     [("EU adopts world's first comprehensive AI law", "https://www.reuters.com/technology/eu-ai-act-adopted-2024/", "Reuters"),
      ("What the EU AI Act means for tech companies", "https://techcrunch.com/2024/eu-ai-act-explainer/", "TechCrunch")]),

    ("EU AI Act enforcement",
     "AI use restrictions crystallizing into hard rules", ["AI Governance"],
     "EU AI Office releases detailed guidelines on prohibited AI practices effective February 2025, including social scoring, emotion recognition at work, and untargeted facial recognition.",
     12, "Euractiv", "https://www.euractiv.com/2024/ai-office-prohibited-practices-guidelines/", "",
     [("EU AI Office details banned AI uses", "https://www.euractiv.com/2024/ai-office-prohibited-practices-guidelines/", "Euractiv")]),

    ("EU AI Act enforcement",
     "GPAI code of practice shaping model obligations", ["AI Governance"],
     "EU AI Office finalizes Code of Practice for General-Purpose AI models, setting transparency, safety testing, and copyright compliance requirements for foundation model providers.",
     9, "TechCrunch", "https://techcrunch.com/2025/eu-gpai-code-of-practice/", "",
     [("EU finalizes code of practice for GPAI models", "https://techcrunch.com/2025/eu-gpai-code-of-practice/", "TechCrunch"),
      ("What the GPAI code means for OpenAI, Google, Meta", "https://www.theverge.com/2025/gpai-code-practice-implications/", "The Verge"),
      ("AI companies face new EU transparency rules", "https://www.reuters.com/technology/gpai-code-practice-2025/", "Reuters")]),

    ("EU AI Act enforcement",
     "Active enforcement of AI compliance beginning", ["AI Governance", "Regulatory & Antitrust"],
     "EU AI Office begins compliance audits of general-purpose AI providers, requesting documentation from OpenAI, Google, and Meta on model training and risk assessments.",
     6, "TechCrunch", "https://techcrunch.com/2025/eu-ai-act-compliance-audits/", "",
     [("EU starts auditing AI companies under AI Act", "https://techcrunch.com/2025/eu-ai-act-compliance-audits/", "TechCrunch")]),

    ("EU AI Act enforcement",
     "High-risk AI system registration deadline approaching", ["AI Governance", "Regulatory & Antitrust"],
     "EU AI Office reminds providers of August 2025 deadline to register high-risk AI systems in EU database, with healthcare, law enforcement, and hiring systems prioritized.",
     4, "Euractiv", "https://www.euractiv.com/2025/high-risk-ai-registration-deadline/", "",
     [("High-risk AI registration deadline looms", "https://www.euractiv.com/2025/high-risk-ai-registration-deadline/", "Euractiv"),
      ("Companies scramble to classify AI systems under EU law", "https://www.ft.com/content/ai-system-classification-2025", "Financial Times")]),

    ("EU AI Act enforcement",
     "Financial penalties for AI non-compliance emerging", ["AI Governance", "Data Privacy"],
     "EU AI Office issues first fine under AI Act — €15M against Meta for deploying emotion recognition in workplace tools without required assessment.",
     3, "Financial Times", "https://www.ft.com/content/eu-ai-office-meta-fine-2025", "",
     [("Meta hit with first EU AI Act fine", "https://www.ft.com/content/eu-ai-office-meta-fine-2025", "Financial Times")]),

    ("EU AI Act enforcement",
     "AI model transparency norms taking shape", ["AI Governance"],
     "Google DeepMind files general-purpose AI model card and risk assessment for Gemini under AI Act transparency requirements, setting precedent for other providers.",
     2, "The Verge", "https://www.theverge.com/2025/google-ai-act-compliance-report", "",
     [("Google files first AI Act compliance report for Gemini", "https://www.theverge.com/2025/google-ai-act-compliance-report", "The Verge")]),

    ("EU AI Act enforcement",
     "Member states diverging on AI Act implementation", ["AI Governance", "Regulatory & Antitrust"],
     "France and Germany push for lighter AI Act enforcement for European AI startups, clashing with stricter interpretation from Spain and Netherlands, creating fragmentation risk.",
     1, "Politico EU", "https://www.politico.eu/article/ai-act-enforcement-fragmentation-2025/", "",
     [("EU countries split on AI Act enforcement approach", "https://www.politico.eu/article/ai-act-enforcement-fragmentation-2025/", "Politico EU"),
      ("France lobbies for AI startup exemptions", "https://www.lemonde.fr/en/economy/2025/france-ai-act-startups/", "Le Monde")]),

    # ── GDPR cross-border enforcement (5 signals) ──
    ("GDPR cross-border enforcement",
     "Global privacy regimes converging on GDPR model", ["Data Privacy"],
     "India's DPDP Act comes into effect, creating data protection framework for 1.4B people. Cross-border data transfer rules require adequacy determination similar to GDPR.",
     18, "Reuters", "https://www.reuters.com/technology/india-dpdp-act-enacted-2024/", "",
     [("India's data protection law takes effect", "https://www.reuters.com/technology/india-dpdp-act-enacted-2024/", "Reuters")]),

    ("GDPR cross-border enforcement",
     "Cross-border data transfer enforcement escalating", ["Data Privacy", "Regulatory & Antitrust"],
     "Irish DPC issues record GDPR fine against Meta for transferring EU user data to US without adequate safeguards, despite new Data Privacy Framework.",
     14, "BBC News", "https://www.bbc.com/news/technology-meta-gdpr-fine-2024", "",
     [("Meta hit with record €1.2B GDPR fine", "https://www.bbc.com/news/technology-meta-gdpr-fine-2024", "BBC News")]),

    ("GDPR cross-border enforcement",
     "Privacy compliance fragmentation accelerating", ["Data Privacy"],
     "With 15 US states now having comprehensive privacy laws and no federal standard, companies face growing compliance fragmentation across jurisdictions.",
     8, "IAPP", "https://iapp.org/news/2025-state-privacy-law-tracker/", "",
     [("US privacy law patchwork reaches 15 states", "https://iapp.org/news/2025-state-privacy-law-tracker/", "IAPP")]),

    ("GDPR cross-border enforcement",
     "GDPR enforcement coordination tightening across DPAs", ["Data Privacy", "Regulatory & Antitrust"],
     "European Data Protection Board launches coordinated enforcement action across 12 DPAs targeting AI training data practices, signaling unified approach to emerging tech issues.",
     5, "Euractiv", "https://www.euractiv.com/2025/edpb-coordinated-ai-enforcement/", "",
     [("EU privacy watchdogs launch coordinated AI data probe", "https://www.euractiv.com/2025/edpb-coordinated-ai-enforcement/", "Euractiv"),
      ("EDPB targets AI training data under GDPR", "https://www.reuters.com/technology/edpb-ai-training-data-2025/", "Reuters")]),

    ("GDPR cross-border enforcement",
     "AI training data entering privacy frameworks", ["Data Privacy", "AI Governance"],
     "EU and Japan renew mutual data adequacy decision with new provisions requiring AI training data to comply with GDPR principles, expanding cross-border framework.",
     3, "Nikkei Asia", "https://asia.nikkei.com/eu-japan-data-adequacy-ai-2025", "",
     [("EU-Japan data deal adds AI training requirements", "https://asia.nikkei.com/eu-japan-data-adequacy-ai-2025", "Nikkei Asia")]),

    # ── AI content labeling mandates (5 signals) ──
    ("AI content labeling mandates",
     "Growing push for mandatory AI content labels", ["AI Governance", "Content Moderation"],
     "US senators introduce bipartisan bill requiring AI-generated content to carry visible labels and metadata watermarks, targeting both text and image generation.",
     16, "Politico", "https://www.politico.com/news/2024/ai-labeling-bill-senate/", "",
     [("Senate introduces AI content labeling bill", "https://www.politico.com/news/2024/ai-labeling-bill-senate/", "Politico")]),

    ("AI content labeling mandates",
     "Election deepfakes accelerating labeling urgency", ["AI Governance", "Content Moderation"],
     "Viral AI-generated political deepfakes during 2024 elections accelerate platform and regulatory push for mandatory content provenance and labeling standards.",
     12, "NPR", "https://www.npr.org/2024/deepfake-elections-labeling-push/", "",
     [("Election deepfakes drive AI labeling urgency", "https://www.npr.org/2024/deepfake-elections-labeling-push/", "NPR")]),

    ("AI content labeling mandates",
     "Tech platforms adopting voluntary AI labels", ["AI Governance", "Content Moderation"],
     "Meta, Google, and OpenAI jointly announce voluntary AI content labeling commitments at Munich Security Conference, labeling AI-generated images across platforms by mid-2025.",
     9, "The Verge", "https://www.theverge.com/2025/tech-voluntary-ai-labeling-commitments/", "",
     [("Big tech pledges voluntary AI content labels", "https://www.theverge.com/2025/tech-voluntary-ai-labeling-commitments/", "The Verge"),
      ("Tech companies promise to label AI content", "https://www.reuters.com/technology/ai-labeling-pledges-2025/", "Reuters")]),

    ("AI content labeling mandates",
     "State-level AI provenance laws materializing", ["AI Governance", "Content Moderation"],
     "California signs into law AB-1234 requiring all AI-generated images, audio, and video to carry C2PA provenance metadata, with penalties for removal.",
     6, "Ars Technica", "https://arstechnica.com/2025/california-ai-labeling-law/", "",
     [("California passes strict AI content labeling law", "https://arstechnica.com/2025/california-ai-labeling-law/", "Ars Technica")]),

    ("AI content labeling mandates",
     "Industry converging on C2PA provenance standard", ["AI Governance", "Content Moderation"],
     "Google and Meta announce adoption of C2PA content provenance standard across all AI generation tools, ahead of California's enforcement deadline.",
     3, "The Verge", "https://www.theverge.com/2025/google-meta-c2pa-watermarking/", "",
     [("Google and Meta embrace AI watermarking standard", "https://www.theverge.com/2025/google-meta-c2pa-watermarking/", "The Verge")]),

    # ── DMA platform compliance (7 signals) ──
    ("DMA platform compliance",
     "Platform gatekeeper regime taking hold", ["Competition & Market Power", "Regulatory & Antitrust"],
     "EU Commission finalizes gatekeeper designations under DMA for Alphabet, Apple, Meta, Amazon, Microsoft, and ByteDance across 22 core platform services.",
     26, "European Commission", "https://ec.europa.eu/commission/presscorner/detail/en/ip_23_4328", "",
     [("EU names six tech giants as DMA gatekeepers", "https://ec.europa.eu/commission/presscorner/detail/en/ip_23_4328", "European Commission")]),

    ("DMA platform compliance",
     "Forced platform openness reshaping app economy", ["Competition & Market Power"],
     "Apple begins allowing third-party app stores on iOS in EU to comply with DMA, while maintaining core technology fee that developers criticize as circumvention.",
     16, "The Verge", "https://www.theverge.com/2024/apple-ios-third-party-app-stores-dma/", "",
     [("Apple reluctantly opens iOS to rival app stores", "https://www.theverge.com/2024/apple-ios-third-party-app-stores-dma/", "The Verge")]),

    ("DMA platform compliance",
     "Google choice screen rollout reshaping search defaults", ["Competition & Market Power", "Regulatory & Antitrust"],
     "Google deploys DMA-mandated search engine choice screen across Android devices in EU, with early data showing 15% of users switching away from Google Search as default.",
     12, "Reuters", "https://www.reuters.com/technology/google-choice-screen-dma-2024/", "",
     [("Google rolls out choice screen in EU under DMA", "https://www.reuters.com/technology/google-choice-screen-dma-2024/", "Reuters"),
      ("15% of EU Android users switch search engine", "https://www.theverge.com/2024/google-choice-screen-results/", "The Verge"),
      ("DMA choice screen denting Google search share", "https://arstechnica.com/2024/dma-google-search-share/", "Ars Technica")]),

    ("DMA platform compliance",
     "Messaging interoperability becoming reality", ["Competition & Market Power"],
     "Meta's WhatsApp launches interoperability features allowing messages from Signal and Telegram users, complying with DMA messaging requirements.",
     8, "TechCrunch", "https://techcrunch.com/2025/whatsapp-interoperability-signal-telegram/", "",
     [("WhatsApp opens messaging to rival apps under DMA", "https://techcrunch.com/2025/whatsapp-interoperability-signal-telegram/", "TechCrunch")]),

    ("DMA platform compliance",
     "Meta fined for pay-or-consent DMA violation", ["Competition & Market Power", "Data Privacy"],
     "EU Commission fines Meta €800M for 'pay or consent' model that charges users for ad-free Facebook/Instagram, ruling it violates DMA's prohibition on bundling consent with service access.",
     5, "Financial Times", "https://www.ft.com/content/meta-pay-consent-dma-fine-2025", "",
     [("EU fines Meta €800M over pay-or-consent model", "https://www.ft.com/content/meta-pay-consent-dma-fine-2025", "Financial Times"),
      ("Meta's ad-free subscription model ruled DMA violation", "https://www.reuters.com/technology/meta-dma-fine-2025/", "Reuters")]),

    ("DMA platform compliance",
     "DMA enforcement teeth showing with major fines", ["Competition & Market Power", "Regulatory & Antitrust"],
     "EU Commission fines Apple for DMA non-compliance on App Store steering rules, finding core technology fee effectively prevents developer adoption of alternatives.",
     3, "Bloomberg", "https://www.bloomberg.com/news/articles/eu-fines-apple-dma-2025", "",
     [("EU hits Apple with €500M DMA fine", "https://www.bloomberg.com/news/articles/eu-fines-apple-dma-2025", "Bloomberg")]),

    ("DMA platform compliance",
     "DMA compliance reviews expanding to new services", ["Competition & Market Power", "Regulatory & Antitrust"],
     "EU Commission opens DMA compliance investigations into Amazon's Buy Box algorithm and Microsoft's Teams-Office bundling, signaling broader enforcement beyond initial targets.",
     1, "Politico EU", "https://www.politico.eu/article/dma-amazon-microsoft-investigations-2025/", "",
     [("EU opens new DMA probes into Amazon, Microsoft", "https://www.politico.eu/article/dma-amazon-microsoft-investigations-2025/", "Politico EU"),
      ("DMA enforcement widens beyond Apple and Google", "https://techcrunch.com/2025/dma-enforcement-expansion/", "TechCrunch")]),

    # ── Digital services tax fragmentation (5 signals) ──
    ("Digital services tax fragmentation",
     "Multilateral digital tax consensus unraveling", ["Taxation & Digital Services"],
     "OECD global tax deal faces ratification delays as US Senate signals opposition, threatening to unravel multilateral approach to digital services taxation.",
     20, "Financial Times", "https://www.ft.com/content/oecd-pillar-one-stalls-2024", "",
     [("OECD digital tax deal faces collapse", "https://www.ft.com/content/oecd-pillar-one-stalls-2024", "Financial Times")]),

    ("Digital services tax fragmentation",
     "Unilateral digital tax proliferation accelerating", ["Taxation & Digital Services"],
     "Brazil, Nigeria, Kenya, Thailand, and Vietnam announce unilateral digital services taxes as OECD Pillar One stalls, adding to growing patchwork of 40+ country-level levies.",
     12, "The Economist", "https://www.economist.com/2024/digital-services-tax-proliferation/", "",
     [("Digital tax fragmentation accelerates globally", "https://www.economist.com/2024/digital-services-tax-proliferation/", "The Economist")]),

    ("Digital services tax fragmentation",
     "Digital tax disputes escalating to trade conflict", ["Taxation & Digital Services", "Regulatory & Antitrust"],
     "US Trade Representative announces Section 301 investigation into digital services taxes in 8 countries, threatening retaliatory tariffs on goods imports.",
     6, "Reuters", "https://www.reuters.com/business/us-tariff-threat-digital-taxes-2025/", "",
     [("US threatens tariffs over foreign digital taxes", "https://www.reuters.com/business/us-tariff-threat-digital-taxes-2025/", "Reuters")]),

    ("Digital services tax fragmentation",
     "OECD Pillar One collapse becoming likely", ["Taxation & Digital Services"],
     "OECD Secretary-General warns Pillar One multilateral convention may not achieve minimum ratifications by June 2025 deadline, effectively confirming collapse of unified approach.",
     4, "Financial Times", "https://www.ft.com/content/oecd-pillar-one-collapse-warning-2025", "",
     [("OECD digital tax deal on verge of collapse", "https://www.ft.com/content/oecd-pillar-one-collapse-warning-2025", "Financial Times"),
      ("Global digital tax agreement falters", "https://www.reuters.com/business/oecd-pillar-one-deadline-2025/", "Reuters")]),

    ("Digital services tax fragmentation",
     "Digital tax costs flowing through to customers", ["Taxation & Digital Services", "Competition & Market Power"],
     "Google begins passing digital services tax surcharges to advertisers in 12 countries, adding 2-5% fees that disproportionately impact small businesses.",
     2, "Ad Age", "https://adage.com/article/digital-marketing-ad-tech-news/google-digital-tax-surcharge/", "",
     [("Google adds digital tax surcharges for advertisers", "https://adage.com/article/digital-marketing-ad-tech-news/google-digital-tax-surcharge/", "Ad Age")]),
]

_SG_MANPOWER_SEEDS = [
    # ── Platform worker CPF protections (8 signals) ──
    ("Platform worker CPF protections",
     "Formalizing gig worker social protections", ["Gig Economy & Platform Work"],
     "MOM establishes advisory committee on platform workers chaired by senior minister, tasked with recommending CPF and insurance frameworks for gig workers.",
     28, "The Straits Times", "https://www.straitstimes.com/singapore/advisory-committee-platform-workers-2023", "",
     [("MOM forms committee on platform worker protections", "https://www.straitstimes.com/singapore/advisory-committee-platform-workers-2023", "The Straits Times")]),

    ("Platform worker CPF protections",
     "Mandatory CPF for gig workers gaining policy weight", ["Gig Economy & Platform Work", "Wage Policy & Progressive Wages"],
     "Advisory committee publishes recommendations for mandatory CPF contributions for platform workers, with phased implementation starting from delivery and ride-hail sectors.",
     22, "Channel NewsAsia", "https://www.channelnewsasia.com/singapore/platform-worker-cpf-recommendations-2024", "",
     [("Gig workers to get CPF under new recommendations", "https://www.channelnewsasia.com/singapore/platform-worker-cpf-recommendations-2024", "Channel NewsAsia")]),

    ("Platform worker CPF protections",
     "Public consultation on platform worker protections", ["Gig Economy & Platform Work"],
     "MOM launches public consultation on Platform Workers Bill, receiving over 5,000 submissions from workers, platforms, and industry groups on CPF contribution rates and coverage scope.",
     18, "The Straits Times", "https://www.straitstimes.com/singapore/platform-worker-bill-consultation-2024", "",
     [("Platform worker bill draws 5,000 consultation responses", "https://www.straitstimes.com/singapore/platform-worker-bill-consultation-2024", "The Straits Times"),
      ("Gig workers push for stronger protections in consultation", "https://www.todayonline.com/singapore/gig-workers-consultation-cpf-2024", "TODAY")]),

    ("Platform worker CPF protections",
     "Platforms preemptively adopting CPF contributions", ["Gig Economy & Platform Work"],
     "Major platforms Grab and Deliveroo launch voluntary CPF contribution pilot programs ahead of legislation, covering 15,000 delivery riders in initial phase.",
     16, "The Business Times", "https://www.businesstimes.com.sg/singapore/grab-deliveroo-cpf-pilot-2024", "",
     [("Grab, Deliveroo start voluntary CPF for riders", "https://www.businesstimes.com.sg/singapore/grab-deliveroo-cpf-pilot-2024", "The Business Times")]),

    ("Platform worker CPF protections",
     "Sector-specific implementation details emerging", ["Gig Economy & Platform Work", "Wage Policy & Progressive Wages"],
     "MOM announces differentiated CPF contribution schedules: ride-hail and delivery from Jan 2026, logistics and private hire from Jul 2026, with age-based phase-in for older workers.",
     12, "Channel NewsAsia", "https://www.channelnewsasia.com/singapore/platform-cpf-sector-schedule-2024", "",
     [("MOM reveals sector-by-sector platform CPF schedule", "https://www.channelnewsasia.com/singapore/platform-cpf-sector-schedule-2024", "Channel NewsAsia"),
      ("Ride-hail drivers first in line for CPF mandate", "https://www.straitstimes.com/singapore/ridehail-cpf-first-2024", "The Straits Times")]),

    ("Platform worker CPF protections",
     "Platform worker legislation reaching Parliament", ["Gig Economy & Platform Work"],
     "Platform Workers Bill tabled in Parliament, mandating CPF contributions split between platform and worker, with work injury compensation and housing loan eligibility.",
     8, "The Straits Times", "https://www.straitstimes.com/singapore/platform-worker-cpf-bill-parliament-2025", "",
     [("Platform worker CPF bill tabled in Parliament", "https://www.straitstimes.com/singapore/platform-worker-cpf-bill-parliament-2025", "The Straits Times")]),

    ("Platform worker CPF protections",
     "Gig worker protections codified into law", ["Gig Economy & Platform Work", "Wage Policy & Progressive Wages"],
     "Parliament passes Platform Workers Act with mandatory CPF contributions starting January 2026. Covers 70,000 workers across ride-hail, delivery, and logistics platforms.",
     4, "Channel NewsAsia", "https://www.channelnewsasia.com/singapore/platform-workers-act-passed-2025", "",
     [("Platform Workers Act passed, CPF from Jan 2026", "https://www.channelnewsasia.com/singapore/platform-workers-act-passed-2025", "Channel NewsAsia")]),

    ("Platform worker CPF protections",
     "CPF costs flowing through to consumer prices", ["Gig Economy & Platform Work", "Wage Policy & Progressive Wages"],
     "Grab and foodpanda raise delivery fees by 5-8% citing mandatory CPF contribution costs. Consumer groups call for government subsidy during transition period.",
     2, "TODAY", "https://www.todayonline.com/singapore/delivery-fees-rise-cpf-platform-workers-2025", "",
     [("Delivery fees rise as platform CPF kicks in", "https://www.todayonline.com/singapore/delivery-fees-rise-cpf-platform-workers-2025", "TODAY")]),

    # ── Foreign workforce COMPASS tightening (8 signals) ──
    ("Foreign workforce COMPASS tightening",
     "Points-based EP screening reshaping hiring", ["Foreign Workforce Policy"],
     "MOM launches Complementarity Assessment Framework (COMPASS) for EP applications, introducing points-based evaluation on salary, qualifications, diversity, and skills bonus.",
     26, "Ministry of Manpower", "https://www.mom.gov.sg/passes-and-permits/employment-pass/compass", "",
     [("COMPASS framework goes live for EP applications", "https://www.mom.gov.sg/passes-and-permits/employment-pass/compass", "Ministry of Manpower")]),

    ("Foreign workforce COMPASS tightening",
     "Rising salary bar for foreign professionals", ["Foreign Workforce Policy"],
     "MOM raises Employment Pass qualifying salary from $5,000 to $5,600 with higher thresholds for financial services sector, affecting renewal and new applications.",
     18, "The Straits Times", "https://www.straitstimes.com/singapore/ep-salary-raised-5600-2024", "",
     [("EP minimum salary raised to $5,600", "https://www.straitstimes.com/singapore/ep-salary-raised-5600-2024", "The Straits Times")]),

    ("Foreign workforce COMPASS tightening",
     "Financial sector facing higher EP thresholds", ["Foreign Workforce Policy"],
     "MOM sets financial services EP qualifying salary at $6,200, the highest sector-specific threshold, amid concerns about over-reliance on foreign talent in banking and fintech.",
     14, "The Business Times", "https://www.businesstimes.com.sg/singapore/financial-sector-ep-threshold-2024", "",
     [("Finance sector EP salary set at $6,200", "https://www.businesstimes.com.sg/singapore/financial-sector-ep-threshold-2024", "The Business Times"),
      ("Banks warn higher EP bar could hurt competitiveness", "https://www.straitstimes.com/business/banking/ep-threshold-banks-2024", "The Straits Times")]),

    ("Foreign workforce COMPASS tightening",
     "Tightening criteria narrowing EP access further", ["Foreign Workforce Policy", "Skills & Training"],
     "MOM announces stricter COMPASS bonus point criteria, raising bar for Skills Bonus and removing Strategic Economic Priorities bonus for overrepresented sectors.",
     10, "The Business Times", "https://www.businesstimes.com.sg/singapore/compass-bonus-tightened-2024", "",
     [("MOM tightens COMPASS bonus point criteria", "https://www.businesstimes.com.sg/singapore/compass-bonus-tightened-2024", "The Business Times")]),

    ("Foreign workforce COMPASS tightening",
     "Startup exemption debates intensifying", ["Foreign Workforce Policy", "Skills & Training"],
     "Tech startup community lobbies for COMPASS exemptions for early-stage companies, arguing points system disadvantages small firms that can't meet salary and diversity thresholds.",
     8, "TechInAsia", "https://www.techinasia.com/singapore-startups-compass-exemption-debate-2025", "",
     [("SG startups push for COMPASS exemptions", "https://www.techinasia.com/singapore-startups-compass-exemption-debate-2025", "TechInAsia"),
      ("Startup founders say COMPASS hurts innovation", "https://www.straitstimes.com/business/startups-compass-2025", "The Straits Times")]),

    ("Foreign workforce COMPASS tightening",
     "Workforce diversity rules disrupting tech hiring", ["Foreign Workforce Policy", "Skills & Training"],
     "EP rejection rates in tech sector double to 30% as COMPASS diversity criterion penalizes firms with high concentration of single-nationality workers.",
     6, "Channel NewsAsia", "https://www.channelnewsasia.com/singapore/tech-ep-rejection-rate-doubles-2025", "",
     [("Tech EP rejections surge under COMPASS", "https://www.channelnewsasia.com/singapore/tech-ep-rejection-rate-doubles-2025", "Channel NewsAsia")]),

    ("Foreign workforce COMPASS tightening",
     "MOM refines COMPASS with startup carve-outs", ["Foreign Workforce Policy"],
     "MOM announces targeted COMPASS adjustments: salary criterion relaxed for companies under 25 employees and less than 3 years old, while maintaining diversity requirements.",
     4, "The Straits Times", "https://www.straitstimes.com/singapore/compass-startup-adjustments-2025", "",
     [("MOM eases COMPASS rules for startups", "https://www.straitstimes.com/singapore/compass-startup-adjustments-2025", "The Straits Times")]),

    ("Foreign workforce COMPASS tightening",
     "COMPASS achieving volume targets, talent gaps emerging", ["Foreign Workforce Policy"],
     "MOM publishes two-year review of COMPASS showing 15% reduction in EP volumes and improved salary benchmarks, while industry groups flag talent shortages in niche roles.",
     2, "The Straits Times", "https://www.straitstimes.com/singapore/compass-two-year-review-2025", "",
     [("COMPASS two-year review shows 15% EP reduction", "https://www.straitstimes.com/singapore/compass-two-year-review-2025", "The Straits Times")]),

    # ── Mid-career AI reskilling gap (7 signals) ──
    ("Mid-career AI reskilling gap",
     "National AI competency standards being defined", ["Skills & Training", "Automation & Job Displacement"],
     "SkillsFuture Singapore publishes national AI skills framework defining competency levels for 12 job families, with training subsidies up to 90% for mid-career workers.",
     24, "SkillsFuture Singapore", "https://www.skillsfuture.gov.sg/ai-skills-framework-2024", "",
     [("SkillsFuture launches national AI skills framework", "https://www.skillsfuture.gov.sg/ai-skills-framework-2024", "SkillsFuture Singapore")]),

    ("Mid-career AI reskilling gap",
     "Widening AI literacy gap among mid-career workers", ["Skills & Training", "Automation & Job Displacement"],
     "National survey finds 65% of professionals, managers, executives, and technicians lack basic AI literacy. Gap is widest among workers aged 45-55 in traditional sectors.",
     16, "The Straits Times", "https://www.straitstimes.com/singapore/ai-skills-gap-survey-pmets-2024", "",
     [("Two-thirds of PMETs lack basic AI skills", "https://www.straitstimes.com/singapore/ai-skills-gap-survey-pmets-2024", "The Straits Times")]),

    ("Mid-career AI reskilling gap",
     "Government tripling AI reskilling ambitions", ["Skills & Training", "Automation & Job Displacement"],
     "Singapore launches National AI Strategy 2.0 with target to train 100,000 workers in AI skills by 2027, tripling SkillsFuture AI course capacity.",
     10, "Channel NewsAsia", "https://www.channelnewsasia.com/singapore/national-ai-strategy-2-reskilling-2024", "",
     [("National AI Strategy 2.0 targets 100K workers", "https://www.channelnewsasia.com/singapore/national-ai-strategy-2-reskilling-2024", "Channel NewsAsia")]),

    ("Mid-career AI reskilling gap",
     "SkillsFuture AI course completion rates disappointing", ["Skills & Training"],
     "Audit reveals only 35% of workers who enroll in SkillsFuture AI courses complete them, with mid-career PMETs citing time constraints and lack of employer support.",
     7, "TODAY", "https://www.todayonline.com/singapore/skillsfuture-ai-course-completion-2025", "",
     [("Only 35% complete SkillsFuture AI courses", "https://www.todayonline.com/singapore/skillsfuture-ai-course-completion-2025", "TODAY"),
      ("Employers urged to give workers time for AI training", "https://www.straitstimes.com/singapore/employer-ai-training-support-2025", "The Straits Times")]),

    ("Mid-career AI reskilling gap",
     "Age divide in AI training uptake deepening", ["Skills & Training", "Aging Workforce & Retirement"],
     "SkillsFuture data shows AI course enrollment by workers over 50 is only 8% of total despite comprising 25% of workforce, prompting targeted outreach programs.",
     5, "TODAY", "https://www.todayonline.com/singapore/ai-reskilling-older-workers-lag-2025", "",
     [("Older workers lag in AI training uptake", "https://www.todayonline.com/singapore/ai-reskilling-older-workers-lag-2025", "TODAY")]),

    ("Mid-career AI reskilling gap",
     "Private sector driving AI literacy expectations", ["Skills & Training"],
     "DBS, OCBC, and Singtel announce mandatory basic AI literacy programs for all employees, signaling private sector push to close AI skills gap.",
     2, "The Business Times", "https://www.businesstimes.com.sg/singapore/dbs-ocbc-singtel-ai-literacy-mandate-2025", "",
     [("Major employers mandate AI literacy for all staff", "https://www.businesstimes.com.sg/singapore/dbs-ocbc-singtel-ai-literacy-mandate-2025", "The Business Times")]),

    ("Mid-career AI reskilling gap",
     "Employer-led AI apprenticeship model launching", ["Skills & Training", "Automation & Job Displacement"],
     "WSG partners with 50 companies to launch AI apprenticeship program placing 2,000 mid-career workers in supervised AI roles, combining on-the-job learning with SkillsFuture modules.",
     1, "Channel NewsAsia", "https://www.channelnewsasia.com/singapore/wsg-ai-apprenticeship-mid-career-2025", "",
     [("WSG launches AI apprenticeship for mid-career workers", "https://www.channelnewsasia.com/singapore/wsg-ai-apprenticeship-mid-career-2025", "Channel NewsAsia")]),

    # ── Progressive wage expansion (7 signals) ──
    ("Progressive wage expansion",
     "Sectoral wage floors expanding steadily", ["Wage Policy & Progressive Wages"],
     "MOM extends Progressive Wage Model to retail sector covering 46,000 workers, setting minimum wage ladder from $1,850 to $2,500 based on skill certification.",
     24, "The Straits Times", "https://www.straitstimes.com/singapore/pwm-retail-sector-2024", "",
     [("PWM extended to retail workers", "https://www.straitstimes.com/singapore/pwm-retail-sector-2024", "The Straits Times")]),

    ("Progressive wage expansion",
     "Progressive wages reaching white-collar roles", ["Wage Policy & Progressive Wages"],
     "Progressive wages for administrators and drivers come into effect, with annual built-in increases of 3-5%. Tripartite partners announce compliance monitoring framework.",
     18, "Channel NewsAsia", "https://www.channelnewsasia.com/singapore/pwm-admin-drivers-2024", "",
     [("Admin and driver progressive wages kick in", "https://www.channelnewsasia.com/singapore/pwm-admin-drivers-2024", "Channel NewsAsia")]),

    ("Progressive wage expansion",
     "F&B sector wage floor covering 72,000 workers", ["Wage Policy & Progressive Wages"],
     "Progressive Wage Model for food services sector takes effect, establishing wage floors for food stall assistants through supervisors with mandatory training hours.",
     10, "TODAY", "https://www.todayonline.com/singapore/food-services-pwm-72000-workers-2024", "",
     [("Food services PWM covers 72,000 workers", "https://www.todayonline.com/singapore/food-services-pwm-72000-workers-2024", "TODAY")]),

    ("Progressive wage expansion",
     "PWM compliance audits revealing gaps among SMEs", ["Wage Policy & Progressive Wages"],
     "MOM releases first PWM compliance audit results: 92% of large employers compliant but only 74% of SMEs meeting requirements, with F&B and retail sectors showing lowest compliance.",
     7, "The Straits Times", "https://www.straitstimes.com/singapore/pwm-compliance-audit-smes-2025", "",
     [("One in four SMEs not meeting progressive wage rules", "https://www.straitstimes.com/singapore/pwm-compliance-audit-smes-2025", "The Straits Times"),
      ("MOM steps up PWM enforcement for SMEs", "https://www.channelnewsasia.com/singapore/pwm-sme-enforcement-2025", "Channel NewsAsia")]),

    ("Progressive wage expansion",
     "Healthcare next sector for wage floor expansion", ["Wage Policy & Progressive Wages"],
     "MOM announces Progressive Wage Model extension to healthcare support workers from 2026, covering nursing aides, patient care assistants, and therapy aides.",
     5, "The Straits Times", "https://www.straitstimes.com/singapore/healthcare-pwm-2026-announcement", "",
     [("Healthcare support workers to get PWM from 2026", "https://www.straitstimes.com/singapore/healthcare-pwm-2026-announcement", "The Straits Times")]),

    ("Progressive wage expansion",
     "SME impact studies showing mixed cost effects", ["Wage Policy & Progressive Wages"],
     "SBTS-commissioned study finds PWM increased labor costs for F&B SMEs by 8-12% but improved retention by 20%, with government wage subsidies offsetting 40% of cost increase.",
     3, "The Business Times", "https://www.businesstimes.com.sg/singapore/pwm-sme-impact-study-2025", "",
     [("PWM raises SME costs 8-12% but cuts turnover", "https://www.businesstimes.com.sg/singapore/pwm-sme-impact-study-2025", "The Business Times")]),

    ("Progressive wage expansion",
     "Momentum building toward universal wage floors", ["Wage Policy & Progressive Wages"],
     "NTUC Secretary-General calls for expanding PWM to all low-wage sectors by 2028, proposing universal coverage as Singapore's alternative to minimum wage.",
     2, "Channel NewsAsia", "https://www.channelnewsasia.com/singapore/ntuc-universal-pwm-coverage-2025", "",
     [("NTUC pushes for universal progressive wage coverage", "https://www.channelnewsasia.com/singapore/ntuc-universal-pwm-coverage-2025", "Channel NewsAsia")]),

    # ── Construction safety crisis (8 signals) ──
    ("Construction safety crisis",
     "Construction safety crisis triggering crackdown", ["Workplace Safety & Health"],
     "MOM reports 46 workplace fatalities in first half of 2024, with construction accounting for 60%. Minister calls emergency meeting with industry leaders.",
     20, "The Straits Times", "https://www.straitstimes.com/singapore/workplace-fatalities-spike-2024", "",
     [("Workplace deaths hit five-year high", "https://www.straitstimes.com/singapore/workplace-fatalities-spike-2024", "The Straits Times")]),

    ("Construction safety crisis",
     "Enforcement intensity ramping up sharply", ["Workplace Safety & Health"],
     "MOM conducts 6-week safety enforcement blitz inspecting 1,200 construction sites, issuing 340 stop-work orders for unsafe working-at-height practices.",
     16, "Channel NewsAsia", "https://www.channelnewsasia.com/singapore/mom-safety-blitz-construction-2024", "",
     [("MOM safety blitz: 340 stop-work orders issued", "https://www.channelnewsasia.com/singapore/mom-safety-blitz-construction-2024", "Channel NewsAsia")]),

    ("Construction safety crisis",
     "Major incident investigation reveals systemic failures", ["Workplace Safety & Health"],
     "MOM investigation into Tuas construction collapse killing 3 workers reveals systematic safety lapses: expired certifications, missing barriers, and subcontractor non-compliance.",
     13, "The Straits Times", "https://www.straitstimes.com/singapore/tuas-collapse-investigation-2024", "",
     [("Tuas collapse probe finds systemic safety failures", "https://www.straitstimes.com/singapore/tuas-collapse-investigation-2024", "The Straits Times"),
      ("Three workers died due to expired safety certs", "https://www.channelnewsasia.com/singapore/tuas-collapse-expired-certs-2024", "Channel NewsAsia"),
      ("Construction industry faces reckoning after Tuas deaths", "https://www.todayonline.com/singapore/construction-safety-reckoning-2024", "TODAY")]),

    ("Construction safety crisis",
     "Safety penalty regime getting significantly harsher", ["Workplace Safety & Health"],
     "Parliament passes Workplace Safety and Health (Amendment) Act doubling maximum fines to $1M and imprisonment to 2 years for negligent employers causing worker deaths.",
     10, "The Straits Times", "https://www.straitstimes.com/singapore/wsh-penalties-doubled-2024", "",
     [("Parliament doubles workplace safety penalties", "https://www.straitstimes.com/singapore/wsh-penalties-doubled-2024", "The Straits Times")]),

    ("Construction safety crisis",
     "Industry pushback on safety cost burden", ["Workplace Safety & Health"],
     "Singapore Contractors Association warns new safety requirements will increase construction costs by 8-15%, requesting government co-funding for safety technology adoption.",
     7, "The Business Times", "https://www.businesstimes.com.sg/singapore/contractors-safety-cost-burden-2025", "",
     [("Contractors warn safety rules will raise costs 15%", "https://www.businesstimes.com.sg/singapore/contractors-safety-cost-burden-2025", "The Business Times"),
      ("Construction firms seek safety tech subsidies", "https://www.straitstimes.com/singapore/construction-safety-subsidies-2025", "The Straits Times")]),

    ("Construction safety crisis",
     "Tech-driven safety monitoring becoming mandatory", ["Workplace Safety & Health", "Automation & Job Displacement"],
     "MOM mandates AI-powered safety monitoring systems including wearable sensors and drone inspections for all construction projects above 10 storeys, effective mid-2025.",
     5, "The Business Times", "https://www.businesstimes.com.sg/singapore/smart-safety-tech-mandate-construction-2025", "",
     [("MOM mandates smart safety tech for construction", "https://www.businesstimes.com.sg/singapore/smart-safety-tech-mandate-construction-2025", "The Business Times")]),

    ("Construction safety crisis",
     "Safety measures showing early measurable improvement", ["Workplace Safety & Health"],
     "MOM Q1 2025 data shows 25% drop in construction major injuries, attributed to enforcement blitz and new penalty regime. Fatality data still pending.",
     3, "Channel NewsAsia", "https://www.channelnewsasia.com/singapore/construction-injuries-drop-q1-2025", "",
     [("Construction injuries drop 25% in Q1 2025", "https://www.channelnewsasia.com/singapore/construction-injuries-drop-q1-2025", "Channel NewsAsia")]),

    ("Construction safety crisis",
     "Crackdown showing measurable safety improvements", ["Workplace Safety & Health"],
     "MOM reports 35% reduction in construction fatalities following enforcement blitz, penalty increases, and tech mandates. Industry calls for permanent adoption of measures.",
     2, "Channel NewsAsia", "https://www.channelnewsasia.com/singapore/construction-fatalities-drop-35-percent-2025", "",
     [("Construction deaths fall 35% after safety push", "https://www.channelnewsasia.com/singapore/construction-fatalities-drop-35-percent-2025", "Channel NewsAsia")]),

    # ── Retirement age and gig work shift (6 signals) ──
    ("Retirement age and gig work shift",
     "Statutory working age steadily extending", ["Aging Workforce & Retirement"],
     "Singapore raises statutory retirement age to 63 and re-employment age to 68 from July 2024, with further increases planned to 65/70 by 2030.",
     20, "Ministry of Manpower", "https://www.mom.gov.sg/retirement-age-2024", "",
     [("Retirement age goes up to 63", "https://www.mom.gov.sg/retirement-age-2024", "Ministry of Manpower")]),

    ("Retirement age and gig work shift",
     "Older workers shifting to gig over re-employment", ["Aging Workforce & Retirement", "Gig Economy & Platform Work"],
     "Survey shows 28% of workers aged 63-68 prefer gig platform work over employer re-employment, citing flexibility. Raises questions about CPF adequacy for gig retirees.",
     14, "The Straits Times", "https://www.straitstimes.com/singapore/seniors-prefer-gig-work-2024", "",
     [("More seniors choosing Grab over re-employment", "https://www.straitstimes.com/singapore/seniors-prefer-gig-work-2024", "The Straits Times")]),

    ("Retirement age and gig work shift",
     "CPF adequacy concerns for gig-working seniors", ["Aging Workforce & Retirement", "Gig Economy & Platform Work"],
     "CPF Board study finds seniors in gig work accumulate 40% less retirement savings than re-employed peers, highlighting coverage gap before Platform Workers Act takes effect.",
     10, "Channel NewsAsia", "https://www.channelnewsasia.com/singapore/cpf-gig-seniors-savings-gap-2024", "",
     [("Gig-working seniors face 40% retirement savings gap", "https://www.channelnewsasia.com/singapore/cpf-gig-seniors-savings-gap-2024", "Channel NewsAsia"),
      ("CPF adequacy at risk as seniors shift to gig work", "https://www.todayonline.com/singapore/cpf-gig-seniors-2024", "TODAY")]),

    ("Retirement age and gig work shift",
     "Retirement age 65 pathway being formalized", ["Aging Workforce & Retirement"],
     "MOM publishes detailed implementation roadmap for raising retirement age to 65 by 2030, including employer transition support and CPF adjustment schedules.",
     6, "Channel NewsAsia", "https://www.channelnewsasia.com/singapore/retirement-age-65-roadmap-2025", "",
     [("MOM lays out retirement age 65 roadmap", "https://www.channelnewsasia.com/singapore/retirement-age-65-roadmap-2025", "Channel NewsAsia")]),

    ("Retirement age and gig work shift",
     "Employers adapting job redesign for older workers", ["Aging Workforce & Retirement", "Skills & Training"],
     "Tripartite alliance publishes job redesign guidelines for workers aged 60+, with case studies from 30 companies showing productivity gains from flexible arrangements and AI-assisted workflows.",
     3, "The Straits Times", "https://www.straitstimes.com/singapore/job-redesign-older-workers-guidelines-2025", "",
     [("New guidelines help firms redesign jobs for older workers", "https://www.straitstimes.com/singapore/job-redesign-older-workers-guidelines-2025", "The Straits Times")]),

    ("Retirement age and gig work shift",
     "Record older worker participation validating policies", ["Aging Workforce & Retirement"],
     "Labour force participation rate for residents aged 55-64 reaches record 70%, driven by re-employment policies and gig economy opportunities.",
     2, "The Straits Times", "https://www.straitstimes.com/singapore/silver-workforce-participation-record-2025", "",
     [("Record 70% of older residents in workforce", "https://www.straitstimes.com/singapore/silver-workforce-participation-record-2025", "The Straits Times")]),

    # ── GenAI workforce displacement (6 signals) ──
    ("GenAI workforce displacement",
     "Corporate AI automation investment surging", ["Automation & Job Displacement"],
     "Singapore's largest employers including DBS, SIA, and Singtel triple AI automation budgets, with internal forecasts projecting 15-20% reduction in back-office roles by 2027.",
     18, "The Business Times", "https://www.businesstimes.com.sg/singapore/firms-triple-ai-automation-investment-2024", "",
     [("Major firms triple AI automation budgets", "https://www.businesstimes.com.sg/singapore/firms-triple-ai-automation-investment-2024", "The Business Times")]),

    ("GenAI workforce displacement",
     "Scale of AI job exposure coming into focus", ["Automation & Job Displacement", "Skills & Training"],
     "MOM-commissioned study finds 23% of Singapore jobs are highly exposed to generative AI disruption, concentrated in admin, finance, and customer service roles.",
     12, "Channel NewsAsia", "https://www.channelnewsasia.com/singapore/mom-study-23-percent-jobs-ai-exposed-2024", "",
     [("Nearly 1 in 4 SG jobs highly exposed to AI", "https://www.channelnewsasia.com/singapore/mom-study-23-percent-jobs-ai-exposed-2024", "Channel NewsAsia")]),

    ("GenAI workforce displacement",
     "AI augmentation outpacing full displacement", ["Automation & Job Displacement", "Skills & Training"],
     "IMDA study finds 70% of AI adoption in Singapore firms augments rather than replaces workers, but role compositions shifting significantly with routine tasks automated.",
     9, "The Straits Times", "https://www.straitstimes.com/singapore/imda-ai-augmentation-study-2025", "",
     [("Most AI adoption augments rather than replaces workers", "https://www.straitstimes.com/singapore/imda-ai-augmentation-study-2025", "The Straits Times"),
      ("AI reshaping jobs more than eliminating them", "https://www.businesstimes.com.sg/singapore/ai-augmentation-jobs-2025", "The Business Times")]),

    ("GenAI workforce displacement",
     "AI-driven job displacement materializing in finance", ["Automation & Job Displacement"],
     "Two mid-size financial institutions announce combined 800 redundancies citing AI automation of loan processing and customer service, with redeployment offered to 60%.",
     6, "The Straits Times", "https://www.straitstimes.com/business/ai-layoffs-financial-sector-2025", "",
     [("800 financial sector jobs cut as AI takes over", "https://www.straitstimes.com/business/ai-layoffs-financial-sector-2025", "The Straits Times")]),

    ("GenAI workforce displacement",
     "Public sector AI displacement guidelines released", ["Automation & Job Displacement"],
     "Public Service Division issues guidelines on managing AI-driven role changes in civil service, mandating 6-month transition support and internal redeployment before any redundancies.",
     4, "Channel NewsAsia", "https://www.channelnewsasia.com/singapore/psd-ai-civil-service-guidelines-2025", "",
     [("Civil service issues AI displacement guidelines", "https://www.channelnewsasia.com/singapore/psd-ai-civil-service-guidelines-2025", "Channel NewsAsia")]),

    ("GenAI workforce displacement",
     "Safety net for AI-displaced workers emerging", ["Automation & Job Displacement", "Skills & Training"],
     "MOM and NTUC pilot AI displacement insurance scheme providing 6 months of salary support and mandatory reskilling for workers displaced by AI automation.",
     2, "TODAY", "https://www.todayonline.com/singapore/ai-displacement-insurance-pilot-2025", "",
     [("New insurance scheme for AI-displaced workers", "https://www.todayonline.com/singapore/ai-displacement-insurance-pilot-2025", "TODAY")]),
]


def _build_signals(seeds, domain: str) -> List[Signal]:
    """Convert seed tuples into Signal objects with distributed timestamps."""
    now = datetime.now(timezone.utc)
    signals = []
    for entry in seeds:
        (topic, title, categories, description, month_offset,
         source_name, source_url, source_quote, related_articles_raw) = entry

        # Spread timestamps with some jitter (date only, no time component)
        base_date = now - timedelta(days=month_offset * 30)
        jitter = random.randint(-5, 5)
        timestamp = (base_date + timedelta(days=jitter)).replace(hour=0, minute=0, second=0, microsecond=0)

        source_articles = [
            SourceArticle(title=ra[0], url=ra[1], source=ra[2])
            for ra in related_articles_raw
        ]

        signal = Signal(
            domain=domain,
            topic=topic,
            categories=categories,
            title=title,
            description=description,
            strength_score=1,  # placeholder, will be computed
            reasoning="",
            sources=[source_name],
            source_url=source_url,
            source_quote=source_quote,
            source_articles=source_articles,
            timestamp=timestamp,
        )
        score_signal(signal)
        signals.append(signal)

    return signals


def seed_if_empty(domain_name: str):
    """Seed signals for a domain if none exist."""
    existing = load_signals(domain_name)
    if existing:
        return

    if domain_name == "Big Tech Policy":
        signals = _build_signals(_BIG_TECH_SEEDS, domain_name)
    elif domain_name == "Singapore Manpower":
        signals = _build_signals(_SG_MANPOWER_SEEDS, domain_name)
    else:
        return

    save_signals(domain_name, signals)
