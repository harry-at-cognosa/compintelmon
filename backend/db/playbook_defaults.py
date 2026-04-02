"""
Default playbook template records for all 4 subject types.
55 total: 19 company, 12 product, 12 service, 12 topic.

Each dict maps to the playbook_templates table columns.

NOTE: Only sources with working collectors (url_template-based crawl4ai, feedparser, httpx)
are enabled by default. Sources requiring unimplemented tools (playwright, tweepy, praw)
or search/API-based collection are disabled until those collectors are built.
"""


def _company_templates() -> list[dict]:
    T = "company"
    return [
        {
            "subject_type": T, "category_key": "website_main", "category_name": "Corporate Website",
            "category_group": "web", "default_enabled": True, "default_frequency_minutes": 360,
            "collection_tool": "crawl4ai", "priority": 1,
            "description": "Monitor the company's main website for messaging, positioning, and structural changes.",
            "signal_instructions": (
                "Crawl the company's main website. Detect changes to homepage messaging, product positioning, "
                "leadership team, and 'about' pages. Flag any new acquisitions, partnerships, or strategic "
                "messaging changes. Compare against previous snapshot."
            ),
            "user_inputs_schema": {
                "type": "object", "required": ["website_url"],
                "properties": {"website_url": {"type": "string", "format": "uri", "title": "Company Website URL"}}
            },
            "collection_config": {"tool": "crawl4ai", "url_template": "{website_url}", "crawl_depth": 0, "extract_mode": "markdown", "max_pages": 1, "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "website_blog", "category_name": "Blog / Newsroom",
            "category_group": "web", "default_enabled": True, "default_frequency_minutes": 120,
            "collection_tool": "feedparser", "priority": 2,
            "description": "Monitor company blog and newsroom for announcements and strategy signals.",
            "signal_instructions": (
                "Monitor the company blog and newsroom. Look for product announcements, partnership news, "
                "leadership changes, and thought leadership pieces that signal strategy shifts. Use RSS if "
                "available; otherwise crawl the blog listing page."
            ),
            "user_inputs_schema": {
                "type": "object",
                "properties": {
                    "blog_url": {"type": "string", "format": "uri", "title": "Blog URL"},
                    "rss_url": {"type": "string", "format": "uri", "title": "RSS Feed URL"},
                }
            },
            "collection_config": {"tool": "feedparser", "url_template": "{rss_url}", "fallback_tool": "crawl4ai", "fallback_url_template": "{blog_url}", "max_entries": 20},
        },
        {
            "subject_type": T, "category_key": "website_pricing", "category_name": "Pricing Page",
            "category_group": "web", "default_enabled": False, "default_frequency_minutes": 1440,
            "collection_tool": "playwright", "priority": 3,
            "description": "Monitor pricing page for plan, price, and feature changes.",
            "signal_instructions": (
                "Monitor the pricing page for changes to plan names, price points, feature inclusions, and tier "
                "structure. Use Playwright for JS-rendered pricing with toggles/sliders. Capture a structured "
                "snapshot of all plans and prices."
            ),
            "user_inputs_schema": {
                "type": "object",
                "properties": {"pricing_url": {"type": "string", "format": "uri", "title": "Pricing Page URL"}}
            },
            "collection_config": {"tool": "playwright", "url_template": "{pricing_url}", "wait_for_selector": "[class*='pricing'], [class*='plan']", "extract_mode": "structured", "timeout_seconds": 45},
        },
        {
            "subject_type": T, "category_key": "website_changelog", "category_name": "Changelog / Release Notes",
            "category_group": "web", "default_enabled": True, "default_frequency_minutes": 360,
            "collection_tool": "crawl4ai", "priority": 4,
            "description": "Monitor changelog for new features, fixes, and deprecations.",
            "signal_instructions": (
                "Monitor changelog or release notes page for new feature releases, bug fixes, deprecations, "
                "and API changes. Extract version numbers, dates, and feature descriptions."
            ),
            "user_inputs_schema": {
                "type": "object",
                "properties": {"changelog_url": {"type": "string", "format": "uri", "title": "Changelog URL"}}
            },
            "collection_config": {"tool": "crawl4ai", "url_template": "{changelog_url}", "extract_mode": "markdown", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "website_careers", "category_name": "Careers / Job Postings",
            "category_group": "web", "default_enabled": True, "default_frequency_minutes": 1440,
            "collection_tool": "crawl4ai", "priority": 5,
            "description": "Track job listings for hiring patterns and strategic direction signals.",
            "signal_instructions": (
                "Scrape job listings. Track total headcount by department. Flag leadership hires (VP+). "
                "Detect strategic patterns: AI/ML hiring = AI investment, Enterprise AEs = upmarket push, "
                "International roles = geographic expansion, Security/compliance = enterprise readiness, "
                "DevRel = ecosystem play. Flag hiring surges or freezes."
            ),
            "user_inputs_schema": {
                "type": "object",
                "properties": {"careers_url": {"type": "string", "format": "uri", "title": "Careers Page URL"}}
            },
            "collection_config": {"tool": "crawl4ai", "url_template": "{careers_url}", "extract_mode": "markdown", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "website_docs", "category_name": "Developer Documentation",
            "category_group": "web", "default_enabled": False, "default_frequency_minutes": 1440,
            "collection_tool": "crawl4ai", "priority": 6,
            "description": "Monitor developer docs for API changes and new integrations.",
            "signal_instructions": (
                "Monitor developer docs for API changes, new SDKs, deprecated features, and new integration "
                "partners. Focus on the changelog or 'what's new' section if available."
            ),
            "user_inputs_schema": {
                "type": "object",
                "properties": {"docs_url": {"type": "string", "format": "uri", "title": "Documentation URL"}}
            },
            "collection_config": {"tool": "crawl4ai", "url_template": "{docs_url}", "extract_mode": "markdown", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "social_twitter", "category_name": "Twitter / X",
            "category_group": "social", "default_enabled": False, "default_frequency_minutes": 60,
            "collection_tool": "tweepy", "priority": 7,
            "description": "Monitor official Twitter/X account and brand mentions.",
            "signal_instructions": (
                "Monitor the company's official Twitter/X account. Track announcements, product teasers, "
                "executive statements, and engagement patterns. Also search for brand mentions. "
                "Flag tweets with high engagement. Requires Twitter API key in group settings."
            ),
            "user_inputs_schema": {
                "type": "object",
                "properties": {"twitter_handle": {"type": "string", "title": "Twitter Handle (without @)"}}
            },
            "collection_config": {"tool": "tweepy", "mode": "user_timeline", "user_template": "{twitter_handle}", "max_tweets": 50, "requires_group_setting": "twitter_bearer_token"},
        },
        {
            "subject_type": T, "category_key": "social_linkedin", "category_name": "LinkedIn",
            "category_group": "social", "default_enabled": False, "default_frequency_minutes": 1440,
            "collection_tool": "crawl4ai", "priority": 8,
            "description": "Monitor LinkedIn company page for employee count and posts.",
            "signal_instructions": (
                "Monitor LinkedIn company page for employee count changes, recent posts, and hiring activity. "
                "Conservative approach — scraping is fragile."
            ),
            "user_inputs_schema": {
                "type": "object",
                "properties": {"linkedin_url": {"type": "string", "format": "uri", "title": "LinkedIn Company URL"}}
            },
            "collection_config": {"tool": "crawl4ai", "url_template": "{linkedin_url}", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "social_reddit", "category_name": "Reddit Mentions",
            "category_group": "social", "default_enabled": False, "default_frequency_minutes": 120,
            "collection_tool": "praw", "priority": 9,
            "description": "Search Reddit for company mentions, complaints, and comparisons.",
            "signal_instructions": (
                "Search Reddit for mentions of the company. Look for customer complaints, praise, feature "
                "requests, competitor comparisons, and insider info. Track sentiment trends. "
                "Requires Reddit API credentials in group settings."
            ),
            "user_inputs_schema": {
                "type": "object",
                "properties": {
                    "reddit_search_terms": {"type": "array", "items": {"type": "string"}, "title": "Search Terms"},
                    "subreddits": {"type": "array", "items": {"type": "string"}, "title": "Subreddits to Monitor"},
                }
            },
            "collection_config": {"tool": "praw", "search_template": "\"{gsubject_name}\"", "sort": "new", "time_filter": "day", "max_results": 50, "requires_group_setting": "reddit_client_id"},
        },
        {
            "subject_type": T, "category_key": "news_general", "category_name": "News & Press",
            "category_group": "news", "default_enabled": False, "default_frequency_minutes": 60,
            "collection_tool": "httpx", "priority": 10,
            "description": "Search news sources for company mentions and breaking stories.",
            "signal_instructions": (
                "Search Google News, Bing News, and industry aggregators for mentions. Look for funding rounds, "
                "acquisitions, lawsuits, executive departures, product launches, outages, and security incidents. "
                "Deduplicate across sources."
            ),
            "user_inputs_schema": {
                "type": "object",
                "properties": {"news_search_terms": {"type": "array", "items": {"type": "string"}, "title": "News Search Terms"}}
            },
            "collection_config": {"tool": "httpx", "search_template": "\"{gsubject_name}\"", "sources": ["google_news", "bing_news"]},
        },
        {
            "subject_type": T, "category_key": "news_press_releases", "category_name": "Press Releases",
            "category_group": "news", "default_enabled": False, "default_frequency_minutes": 360,
            "collection_tool": "feedparser", "priority": 11,
            "description": "Monitor PR Newswire, Business Wire for official press releases.",
            "signal_instructions": (
                "Monitor PR Newswire, Business Wire, GlobeNewswire for official company press releases. "
                "High-signal for M&A, partnerships, and financial results."
            ),
            "user_inputs_schema": {
                "type": "object",
                "properties": {"press_release_sources": {"type": "array", "items": {"type": "string"}, "title": "Press Release RSS Feeds"}}
            },
            "collection_config": {"tool": "feedparser", "sources": ["prnewswire", "businesswire", "globenewswire"]},
        },
        {
            "subject_type": T, "category_key": "regulatory_sec", "category_name": "SEC Filings",
            "category_group": "regulatory", "default_enabled": False, "default_frequency_minutes": 1440,
            "collection_tool": "httpx", "priority": 12,
            "description": "Monitor SEC EDGAR for regulatory filings (US public companies).",
            "signal_instructions": (
                "Monitor SEC EDGAR for 10-K, 10-Q, 8-K, S-1, and DEF14A filings. 8-K filings are especially "
                "time-sensitive (material events). Only relevant for US public companies."
            ),
            "user_inputs_schema": {
                "type": "object",
                "properties": {
                    "sec_cik": {"type": "string", "title": "SEC CIK Number"},
                    "ticker_symbol": {"type": "string", "title": "Ticker Symbol"},
                }
            },
            "collection_config": {"tool": "httpx", "api": "edgar_xbrl"},
        },
        {
            "subject_type": T, "category_key": "regulatory_patents", "category_name": "Patent Filings",
            "category_group": "regulatory", "default_enabled": False, "default_frequency_minutes": 10080,
            "collection_tool": "httpx", "priority": 13,
            "description": "Search patent databases to reveal R&D direction.",
            "signal_instructions": (
                "Search USPTO and Google Patents for new patent applications and grants. Patent filings reveal "
                "R&D direction 12-18 months ahead of product launches."
            ),
            "user_inputs_schema": {
                "type": "object",
                "properties": {"patent_assignee_name": {"type": "string", "title": "Patent Assignee Name"}}
            },
            "collection_config": {"tool": "httpx", "api": "google_patents"},
        },
        {
            "subject_type": T, "category_key": "financial_earnings", "category_name": "Earnings & Financials",
            "category_group": "financial", "default_enabled": False, "default_frequency_minutes": 1440,
            "collection_tool": "httpx", "priority": 14,
            "description": "Monitor earnings reports and financial data (public companies).",
            "signal_instructions": (
                "Monitor for earnings reports, revenue data, guidance changes. Use free APIs "
                "(Alpha Vantage, Yahoo Finance). Only relevant for public companies."
            ),
            "user_inputs_schema": {
                "type": "object",
                "properties": {"ticker_symbol": {"type": "string", "title": "Ticker Symbol"}}
            },
            "collection_config": {"tool": "httpx", "api": "yahoo_finance"},
        },
        {
            "subject_type": T, "category_key": "community_github", "category_name": "GitHub Activity",
            "category_group": "community", "default_enabled": False, "default_frequency_minutes": 360,
            "collection_tool": "httpx", "priority": 15,
            "description": "Monitor GitHub organization for repos, releases, and contributor activity.",
            "signal_instructions": (
                "Monitor GitHub organization for new public repos, star counts, release cadence, contributor "
                "activity, and open issues. Reveals engineering investment and OSS strategy."
            ),
            "user_inputs_schema": {
                "type": "object",
                "properties": {"github_org": {"type": "string", "title": "GitHub Organization"}}
            },
            "collection_config": {"tool": "httpx", "api": "github", "requires_group_setting": "github_token"},
        },
        {
            "subject_type": T, "category_key": "community_glassdoor", "category_name": "Employee Reviews",
            "category_group": "community", "default_enabled": False, "default_frequency_minutes": 10080,
            "collection_tool": "crawl4ai", "priority": 16,
            "description": "Monitor Glassdoor review trends and internal sentiment.",
            "signal_instructions": (
                "Monitor Glassdoor for employee review trends, overall rating changes, and CEO approval. "
                "Internal sentiment often predicts external changes. Scraping is fragile."
            ),
            "user_inputs_schema": {
                "type": "object",
                "properties": {"glassdoor_url": {"type": "string", "format": "uri", "title": "Glassdoor URL"}}
            },
            "collection_config": {"tool": "crawl4ai", "url_template": "{glassdoor_url}", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "website_status", "category_name": "Service Status Page",
            "category_group": "web", "default_enabled": True, "default_frequency_minutes": 30,
            "collection_tool": "httpx", "priority": 17,
            "description": "Monitor status page for uptime, incidents, and outages.",
            "signal_instructions": (
                "Monitor the company's status page. Track uptime, incident frequency, and severity. "
                "Outages are competitive intelligence."
            ),
            "user_inputs_schema": {
                "type": "object",
                "properties": {"status_url": {"type": "string", "format": "uri", "title": "Status Page URL"}}
            },
            "collection_config": {"tool": "httpx", "url_template": "{status_url}", "timeout_seconds": 15},
        },
        {
            "subject_type": T, "category_key": "review_g2", "category_name": "G2 / Capterra Reviews",
            "category_group": "community", "default_enabled": False, "default_frequency_minutes": 10080,
            "collection_tool": "crawl4ai", "priority": 18,
            "description": "Monitor G2 and Capterra for review volume and rating trends.",
            "signal_instructions": (
                "Monitor G2 and Capterra for review volume, average rating trends, and common praise/complaint "
                "themes. Useful for positioning analysis."
            ),
            "user_inputs_schema": {
                "type": "object",
                "properties": {"g2_url": {"type": "string", "format": "uri", "title": "G2 Profile URL"}}
            },
            "collection_config": {"tool": "crawl4ai", "url_template": "{g2_url}", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "web_tech_stack", "category_name": "Technology Stack",
            "category_group": "web", "default_enabled": False, "default_frequency_minutes": 43200,
            "collection_tool": "httpx", "priority": 19,
            "description": "Detect technology stack changes via BuiltWith or Wappalyzer.",
            "signal_instructions": (
                "Detect technology stack changes. Reveals infrastructure decisions, analytics tools, and "
                "marketing tech."
            ),
            "user_inputs_schema": {
                "type": "object",
                "properties": {"website_url": {"type": "string", "format": "uri", "title": "Website URL (reuse)"}}
            },
            "collection_config": {"tool": "httpx", "api": "builtwith"},
        },
    ]


def _product_templates() -> list[dict]:
    T = "product"
    return [
        {
            "subject_type": T, "category_key": "product_page", "category_name": "Product Landing Page",
            "category_group": "web", "default_enabled": True, "default_frequency_minutes": 360,
            "collection_tool": "crawl4ai", "priority": 1,
            "description": "Monitor product page for messaging and feature list changes.",
            "signal_instructions": "Monitor the main product page for messaging changes, feature list updates, positioning shifts, and CTA changes. Diff against previous snapshot.",
            "user_inputs_schema": {"type": "object", "required": ["product_url"], "properties": {"product_url": {"type": "string", "format": "uri", "title": "Product URL"}}},
            "collection_config": {"tool": "crawl4ai", "url_template": "{product_url}", "extract_mode": "markdown", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "product_pricing", "category_name": "Pricing",
            "category_group": "web", "default_enabled": False, "default_frequency_minutes": 1440,
            "collection_tool": "playwright", "priority": 2,
            "description": "Monitor pricing for plan, price, and feature matrix changes.",
            "signal_instructions": "Capture all plans, prices, feature matrices, usage limits. Detect price increases, new tiers, bundling changes. Use Playwright for JS-rendered pricing.",
            "user_inputs_schema": {"type": "object", "properties": {"pricing_url": {"type": "string", "format": "uri", "title": "Pricing URL"}}},
            "collection_config": {"tool": "playwright", "url_template": "{pricing_url}", "wait_for_selector": "[class*='pricing']", "timeout_seconds": 45},
        },
        {
            "subject_type": T, "category_key": "product_changelog", "category_name": "Changelog",
            "category_group": "web", "default_enabled": True, "default_frequency_minutes": 180,
            "collection_tool": "crawl4ai", "priority": 3,
            "description": "Highest-signal source: track feature releases and deprecations.",
            "signal_instructions": "Monitor changelog for new features, improvements, bug fixes, deprecations, breaking changes. Extract version numbers and categorize changes. Highest-signal source for product evolution.",
            "user_inputs_schema": {"type": "object", "properties": {"changelog_url": {"type": "string", "format": "uri", "title": "Changelog URL"}}},
            "collection_config": {"tool": "crawl4ai", "url_template": "{changelog_url}", "extract_mode": "markdown", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "product_docs", "category_name": "Documentation",
            "category_group": "web", "default_enabled": True, "default_frequency_minutes": 1440,
            "collection_tool": "crawl4ai", "priority": 4,
            "description": "Monitor docs for API changes, new integration guides, deprecated features.",
            "signal_instructions": "Monitor product documentation for new pages, API changes, new integration guides, and deprecated features. New doc pages often precede feature launches.",
            "user_inputs_schema": {"type": "object", "properties": {"docs_url": {"type": "string", "format": "uri", "title": "Docs URL"}}},
            "collection_config": {"tool": "crawl4ai", "url_template": "{docs_url}", "extract_mode": "markdown", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "product_api", "category_name": "API Schema",
            "category_group": "web", "default_enabled": False, "default_frequency_minutes": 1440,
            "collection_tool": "httpx", "priority": 5,
            "description": "Monitor OpenAPI/Swagger specs for endpoint changes.",
            "signal_instructions": "Monitor OpenAPI/Swagger specs. Detect new endpoints, deprecated endpoints, new parameters, breaking changes. Download and diff the spec file.",
            "user_inputs_schema": {"type": "object", "properties": {"api_docs_url": {"type": "string", "format": "uri", "title": "API Docs URL"}}},
            "collection_config": {"tool": "httpx", "url_template": "{api_docs_url}", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "product_integrations", "category_name": "Integrations / Marketplace",
            "category_group": "web", "default_enabled": True, "default_frequency_minutes": 1440,
            "collection_tool": "crawl4ai", "priority": 6,
            "description": "Track integration count and newly added partners.",
            "signal_instructions": "Monitor integrations page or marketplace. New integrations signal ecosystem strategy and partnership activity. Track total count and newly added partners.",
            "user_inputs_schema": {"type": "object", "properties": {"integrations_url": {"type": "string", "format": "uri", "title": "Integrations Page URL"}}},
            "collection_config": {"tool": "crawl4ai", "url_template": "{integrations_url}", "extract_mode": "markdown", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "product_reviews", "category_name": "User Reviews",
            "category_group": "community", "default_enabled": True, "default_frequency_minutes": 1440,
            "collection_tool": "crawl4ai", "priority": 7,
            "description": "Monitor G2, Capterra, Product Hunt, app stores for reviews.",
            "signal_instructions": "Monitor G2, Capterra, Product Hunt, and app stores for product reviews. Track average rating, review volume trends, and extract common themes.",
            "user_inputs_schema": {"type": "object", "properties": {"review_urls": {"type": "array", "items": {"type": "string"}, "title": "Review Page URLs"}}},
            "collection_config": {"tool": "crawl4ai", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "product_social", "category_name": "Social Mentions",
            "category_group": "social", "default_enabled": False, "default_frequency_minutes": 120,
            "collection_tool": "praw", "priority": 8,
            "description": "Search Twitter/X and Reddit for product mentions and sentiment.",
            "signal_instructions": "Search Twitter/X and Reddit for product mentions. Complaints, feature requests, 'just switched from/to' posts. Track sentiment.",
            "user_inputs_schema": {"type": "object", "properties": {"search_terms": {"type": "array", "items": {"type": "string"}, "title": "Search Terms"}}},
            "collection_config": {"tool": "praw", "search_template": "\"{gsubject_name}\"", "sort": "new", "max_results": 50},
        },
        {
            "subject_type": T, "category_key": "product_support", "category_name": "Support Forums",
            "category_group": "community", "default_enabled": False, "default_frequency_minutes": 360,
            "collection_tool": "crawl4ai", "priority": 9,
            "description": "Monitor support forums for common complaints and feature requests.",
            "signal_instructions": "Monitor official support forums. Common complaints reveal weaknesses. Feature request threads signal roadmap gaps.",
            "user_inputs_schema": {"type": "object", "properties": {"forum_url": {"type": "string", "format": "uri", "title": "Support Forum URL"}}},
            "collection_config": {"tool": "crawl4ai", "url_template": "{forum_url}", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "product_competitors", "category_name": "Competitor Comparison Pages",
            "category_group": "web", "default_enabled": False, "default_frequency_minutes": 1440,
            "collection_tool": "crawl4ai", "priority": 10,
            "description": "Monitor 'vs competitor' pages for positioning and feature highlights.",
            "signal_instructions": "Monitor the product's 'vs competitor' pages. Track positioning, highlighted features, and which competitors are addressed.",
            "user_inputs_schema": {"type": "object", "properties": {"comparison_urls": {"type": "array", "items": {"type": "string"}, "title": "Comparison Page URLs"}}},
            "collection_config": {"tool": "crawl4ai", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "news_product", "category_name": "Product News Coverage",
            "category_group": "news", "default_enabled": False, "default_frequency_minutes": 120,
            "collection_tool": "httpx", "priority": 11,
            "description": "Search tech news for product reviews and announcements.",
            "signal_instructions": "Search tech news sites for product coverage. Reviews, announcements, comparative articles.",
            "user_inputs_schema": {"type": "object", "properties": {"news_search_terms": {"type": "array", "items": {"type": "string"}, "title": "News Search Terms"}}},
            "collection_config": {"tool": "httpx", "search_template": "\"{gsubject_name}\"", "sources": ["google_news"]},
        },
        {
            "subject_type": T, "category_key": "product_hunt", "category_name": "Product Hunt",
            "category_group": "community", "default_enabled": False, "default_frequency_minutes": 1440,
            "collection_tool": "httpx", "priority": 12,
            "description": "Monitor Product Hunt for launches and community discussion.",
            "signal_instructions": "Monitor Product Hunt for new launches, updates, and community discussion. A competitor PH launch is a high-priority signal.",
            "user_inputs_schema": {"type": "object", "properties": {"product_hunt_slug": {"type": "string", "title": "Product Hunt Slug"}}},
            "collection_config": {"tool": "httpx", "api": "product_hunt"},
        },
    ]


def _service_templates() -> list[dict]:
    T = "service"
    return [
        {
            "subject_type": T, "category_key": "service_page", "category_name": "Service Landing Page",
            "category_group": "web", "default_enabled": True, "default_frequency_minutes": 360,
            "collection_tool": "crawl4ai", "priority": 1,
            "description": "Monitor service page for positioning and messaging changes.",
            "signal_instructions": "Monitor the service's main page for positioning, feature list, and messaging changes. Detect value proposition and target audience changes.",
            "user_inputs_schema": {"type": "object", "required": ["service_url"], "properties": {"service_url": {"type": "string", "format": "uri", "title": "Service URL"}}},
            "collection_config": {"tool": "crawl4ai", "url_template": "{service_url}", "extract_mode": "markdown", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "service_pricing", "category_name": "Pricing / Plans",
            "category_group": "web", "default_enabled": False, "default_frequency_minutes": 1440,
            "collection_tool": "playwright", "priority": 2,
            "description": "Monitor pricing, SLA terms, and usage-based pricing.",
            "signal_instructions": "Plan changes, price adjustments, SLA terms, usage-based pricing components. Use Playwright for interactive calculators.",
            "user_inputs_schema": {"type": "object", "properties": {"pricing_url": {"type": "string", "format": "uri", "title": "Pricing URL"}}},
            "collection_config": {"tool": "playwright", "url_template": "{pricing_url}", "timeout_seconds": 45},
        },
        {
            "subject_type": T, "category_key": "service_status", "category_name": "Status / Uptime",
            "category_group": "web", "default_enabled": True, "default_frequency_minutes": 30,
            "collection_tool": "httpx", "priority": 3,
            "description": "Monitor uptime, incidents, and maintenance windows.",
            "signal_instructions": "Monitor status page for uptime, incidents, maintenance. Track frequency and MTTR. Reliability is a differentiator.",
            "user_inputs_schema": {"type": "object", "properties": {"status_url": {"type": "string", "format": "uri", "title": "Status Page URL"}}},
            "collection_config": {"tool": "httpx", "url_template": "{status_url}", "timeout_seconds": 15},
        },
        {
            "subject_type": T, "category_key": "service_docs", "category_name": "Documentation",
            "category_group": "web", "default_enabled": True, "default_frequency_minutes": 1440,
            "collection_tool": "crawl4ai", "priority": 4,
            "description": "Monitor for new features, API changes, and deprecation notices.",
            "signal_instructions": "New features, API changes, migration guides, deprecation notices.",
            "user_inputs_schema": {"type": "object", "properties": {"docs_url": {"type": "string", "format": "uri", "title": "Docs URL"}}},
            "collection_config": {"tool": "crawl4ai", "url_template": "{docs_url}", "extract_mode": "markdown", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "service_changelog", "category_name": "Changelog",
            "category_group": "web", "default_enabled": True, "default_frequency_minutes": 360,
            "collection_tool": "crawl4ai", "priority": 5,
            "description": "Feature releases, infrastructure changes, deprecations.",
            "signal_instructions": "Feature releases, infrastructure changes, deprecations.",
            "user_inputs_schema": {"type": "object", "properties": {"changelog_url": {"type": "string", "format": "uri", "title": "Changelog URL"}}},
            "collection_config": {"tool": "crawl4ai", "url_template": "{changelog_url}", "extract_mode": "markdown", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "service_blog", "category_name": "Blog",
            "category_group": "web", "default_enabled": True, "default_frequency_minutes": 120,
            "collection_tool": "feedparser", "priority": 6,
            "description": "Announcements, case studies, roadmap signals, partnerships.",
            "signal_instructions": "Monitor the service blog for announcements, case studies, technical posts revealing roadmap direction, and partnership announcements.",
            "user_inputs_schema": {"type": "object", "properties": {"blog_url": {"type": "string", "format": "uri", "title": "Blog URL"}, "rss_url": {"type": "string", "format": "uri", "title": "RSS URL"}}},
            "collection_config": {"tool": "feedparser", "url_template": "{rss_url}", "fallback_tool": "crawl4ai", "fallback_url_template": "{blog_url}", "max_entries": 20},
        },
        {
            "subject_type": T, "category_key": "service_reviews", "category_name": "Reviews & Ratings",
            "category_group": "community", "default_enabled": True, "default_frequency_minutes": 1440,
            "collection_tool": "crawl4ai", "priority": 7,
            "description": "G2, Capterra, TrustRadius rating trends.",
            "signal_instructions": "Monitor G2, Capterra, TrustRadius for service reviews. Track rating trends and common themes.",
            "user_inputs_schema": {"type": "object", "properties": {"review_urls": {"type": "array", "items": {"type": "string"}, "title": "Review URLs"}}},
            "collection_config": {"tool": "crawl4ai", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "service_social", "category_name": "Social Mentions",
            "category_group": "social", "default_enabled": False, "default_frequency_minutes": 120,
            "collection_tool": "praw", "priority": 8,
            "description": "Outage reports, migration stories, feature feedback.",
            "signal_instructions": "Monitor Twitter/X and Reddit for service mentions. Outage reports, migration stories, feature complaints/praise.",
            "user_inputs_schema": {"type": "object", "properties": {"search_terms": {"type": "array", "items": {"type": "string"}, "title": "Search Terms"}}},
            "collection_config": {"tool": "praw", "search_template": "\"{gsubject_name}\"", "sort": "new", "max_results": 50},
        },
        {
            "subject_type": T, "category_key": "service_sla", "category_name": "SLA / Terms of Service",
            "category_group": "web", "default_enabled": True, "default_frequency_minutes": 10080,
            "collection_tool": "crawl4ai", "priority": 9,
            "description": "Detect SLA downgrades and ToS changes (often happen quietly).",
            "signal_instructions": "Monitor SLA pages and Terms of Service for changes. SLA downgrades, new limitations, ToS changes often happen quietly. Diff against previous.",
            "user_inputs_schema": {"type": "object", "properties": {"sla_url": {"type": "string", "format": "uri", "title": "SLA URL"}, "tos_url": {"type": "string", "format": "uri", "title": "ToS URL"}}},
            "collection_config": {"tool": "crawl4ai", "url_template": "{sla_url}", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "service_compliance", "category_name": "Compliance & Certs",
            "category_group": "web", "default_enabled": False, "default_frequency_minutes": 10080,
            "collection_tool": "crawl4ai", "priority": 10,
            "description": "New certifications signal market expansion.",
            "signal_instructions": "Monitor trust/security/compliance page for new certifications (SOC 2, ISO 27001, HIPAA, FedRAMP). New certs signal market expansion.",
            "user_inputs_schema": {"type": "object", "properties": {"compliance_url": {"type": "string", "format": "uri", "title": "Compliance Page URL"}}},
            "collection_config": {"tool": "crawl4ai", "url_template": "{compliance_url}", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "news_service", "category_name": "News Coverage",
            "category_group": "news", "default_enabled": False, "default_frequency_minutes": 120,
            "collection_tool": "httpx", "priority": 11,
            "description": "Outage reports, comparative articles, industry coverage.",
            "signal_instructions": "Search news for service coverage, outage reports, and comparative articles.",
            "user_inputs_schema": {"type": "object", "properties": {"news_search_terms": {"type": "array", "items": {"type": "string"}, "title": "News Search Terms"}}},
            "collection_config": {"tool": "httpx", "search_template": "\"{gsubject_name}\"", "sources": ["google_news"]},
        },
        {
            "subject_type": T, "category_key": "service_integrations", "category_name": "Integrations & Partners",
            "category_group": "web", "default_enabled": True, "default_frequency_minutes": 1440,
            "collection_tool": "crawl4ai", "priority": 12,
            "description": "New and removed integrations.",
            "signal_instructions": "Monitor integrations/partners page for new and removed integrations.",
            "user_inputs_schema": {"type": "object", "properties": {"integrations_url": {"type": "string", "format": "uri", "title": "Integrations Page URL"}}},
            "collection_config": {"tool": "crawl4ai", "url_template": "{integrations_url}", "extract_mode": "markdown", "timeout_seconds": 30},
        },
    ]


def _topic_templates() -> list[dict]:
    T = "topic"
    return [
        {
            "subject_type": T, "category_key": "topic_news", "category_name": "News Coverage",
            "category_group": "news", "default_enabled": False, "default_frequency_minutes": 60,
            "collection_tool": "httpx", "priority": 1,
            "description": "Search news sources for topic-related articles and trend shifts.",
            "signal_instructions": "Search Google News, Bing News, industry outlets for topic-related articles. Detect trend shifts, new entrants, opinion pieces from key voices. Deduplicate.",
            "user_inputs_schema": {"type": "object", "required": ["search_terms"], "properties": {"search_terms": {"type": "array", "items": {"type": "string"}, "title": "Search Terms"}}},
            "collection_config": {"tool": "httpx", "sources": ["google_news", "bing_news"]},
        },
        {
            "subject_type": T, "category_key": "topic_twitter", "category_name": "Twitter / X Discussion",
            "category_group": "social", "default_enabled": False, "default_frequency_minutes": 60,
            "collection_tool": "tweepy", "priority": 2,
            "description": "Monitor topic discussion, trending hashtags, and influential voices.",
            "signal_instructions": "Monitor Twitter/X for topic discussion, trending hashtags, influential voices. Identify emerging narratives and sentiment shifts. Track volume spikes.",
            "user_inputs_schema": {"type": "object", "properties": {"twitter_search_terms": {"type": "array", "items": {"type": "string"}, "title": "Search Terms"}, "hashtags": {"type": "array", "items": {"type": "string"}, "title": "Hashtags"}}},
            "collection_config": {"tool": "tweepy", "mode": "search", "max_tweets": 100, "requires_group_setting": "twitter_bearer_token"},
        },
        {
            "subject_type": T, "category_key": "topic_reddit", "category_name": "Reddit Discussion",
            "category_group": "social", "default_enabled": False, "default_frequency_minutes": 120,
            "collection_tool": "praw", "priority": 3,
            "description": "Monitor subreddits for topic discussion — often leads mainstream coverage.",
            "signal_instructions": "Monitor relevant subreddits. Track post volume, top posts, comment sentiment. Reddit often leads mainstream coverage by days.",
            "user_inputs_schema": {"type": "object", "properties": {"subreddits": {"type": "array", "items": {"type": "string"}, "title": "Subreddits"}, "search_terms": {"type": "array", "items": {"type": "string"}, "title": "Search Terms"}}},
            "collection_config": {"tool": "praw", "sort": "new", "time_filter": "day", "max_results": 50, "requires_group_setting": "reddit_client_id"},
        },
        {
            "subject_type": T, "category_key": "topic_blogs", "category_name": "Industry Blogs",
            "category_group": "web", "default_enabled": False, "default_frequency_minutes": 360,
            "collection_tool": "feedparser", "priority": 4,
            "description": "Monitor analyst and thought leader blogs via RSS.",
            "signal_instructions": "Monitor industry blogs via RSS. Users can add feeds from analysts, thought leaders, and industry publications. Collect and summarize new posts mentioning the topic.",
            "user_inputs_schema": {"type": "object", "properties": {"rss_feeds": {"type": "array", "items": {"type": "string"}, "title": "RSS Feed URLs"}}},
            "collection_config": {"tool": "feedparser", "max_entries": 20},
        },
        {
            "subject_type": T, "category_key": "topic_research", "category_name": "Research Papers",
            "category_group": "web", "default_enabled": False, "default_frequency_minutes": 1440,
            "collection_tool": "httpx", "priority": 5,
            "description": "Search arXiv, Google Scholar for emerging research.",
            "signal_instructions": "Search arXiv, Google Scholar, SSRN for papers related to the topic. Track academic research, emerging technologies, market research reports.",
            "user_inputs_schema": {"type": "object", "properties": {"arxiv_terms": {"type": "array", "items": {"type": "string"}, "title": "arXiv Search Terms"}, "scholar_terms": {"type": "array", "items": {"type": "string"}, "title": "Scholar Search Terms"}}},
            "collection_config": {"tool": "httpx", "api": "arxiv"},
        },
        {
            "subject_type": T, "category_key": "topic_regulatory", "category_name": "Regulatory & Policy",
            "category_group": "regulatory", "default_enabled": False, "default_frequency_minutes": 1440,
            "collection_tool": "httpx", "priority": 6,
            "description": "Monitor government sites for policy changes and enforcement actions.",
            "signal_instructions": "Monitor government websites, Federal Register, EU regulatory sites for policy changes, proposed rules, and enforcement actions.",
            "user_inputs_schema": {"type": "object", "properties": {"regulatory_terms": {"type": "array", "items": {"type": "string"}, "title": "Search Terms"}, "agency_domains": {"type": "array", "items": {"type": "string"}, "title": "Agency Domains"}}},
            "collection_config": {"tool": "httpx", "api": "federal_register"},
        },
        {
            "subject_type": T, "category_key": "topic_events", "category_name": "Conferences & Events",
            "category_group": "web", "default_enabled": False, "default_frequency_minutes": 10080,
            "collection_tool": "crawl4ai", "priority": 7,
            "description": "Monitor conference websites for events, speakers, and topic tracks.",
            "signal_instructions": "Monitor conference websites and event listing pages for upcoming events, speaker lineups, and topic tracks.",
            "user_inputs_schema": {"type": "object", "properties": {"event_urls": {"type": "array", "items": {"type": "string"}, "title": "Event Page URLs"}}},
            "collection_config": {"tool": "crawl4ai", "timeout_seconds": 30},
        },
        {
            "subject_type": T, "category_key": "topic_github", "category_name": "GitHub / OSS Activity",
            "category_group": "community", "default_enabled": False, "default_frequency_minutes": 1440,
            "collection_tool": "httpx", "priority": 8,
            "description": "Search GitHub for trending repos and activity spikes.",
            "signal_instructions": "Search GitHub for trending repos, new projects, activity spikes. Track stars, forks, new repo creation velocity.",
            "user_inputs_schema": {"type": "object", "properties": {"github_search_terms": {"type": "array", "items": {"type": "string"}, "title": "GitHub Search Terms"}}},
            "collection_config": {"tool": "httpx", "api": "github_search"},
        },
        {
            "subject_type": T, "category_key": "topic_hacker_news", "category_name": "Hacker News",
            "category_group": "community", "default_enabled": False, "default_frequency_minutes": 120,
            "collection_tool": "httpx", "priority": 9,
            "description": "Leading indicator for tech trends and developer sentiment.",
            "signal_instructions": "Search Hacker News (Algolia API) for topic-related submissions and comments. HN is a leading indicator for tech trends.",
            "user_inputs_schema": {"type": "object", "properties": {"hn_search_terms": {"type": "array", "items": {"type": "string"}, "title": "HN Search Terms"}}},
            "collection_config": {"tool": "httpx", "api": "hn_algolia"},
        },
        {
            "subject_type": T, "category_key": "topic_wikipedia", "category_name": "Wikipedia Changes",
            "category_group": "web", "default_enabled": False, "default_frequency_minutes": 1440,
            "collection_tool": "httpx", "priority": 10,
            "description": "Monitor Wikipedia pages for edits and evolving definitions.",
            "signal_instructions": "Monitor specific Wikipedia pages for edits. Evolving definitions, controversies, market perception.",
            "user_inputs_schema": {"type": "object", "properties": {"wikipedia_pages": {"type": "array", "items": {"type": "string"}, "title": "Wikipedia Page Titles"}}},
            "collection_config": {"tool": "httpx", "api": "wikipedia"},
        },
        {
            "subject_type": T, "category_key": "topic_podcasts", "category_name": "Podcasts & Video",
            "category_group": "web", "default_enabled": False, "default_frequency_minutes": 1440,
            "collection_tool": "httpx", "priority": 11,
            "description": "Monitor podcast RSS feeds and YouTube channels.",
            "signal_instructions": "Monitor podcast RSS feeds and YouTube channels. Extract titles and descriptions for keyword matching.",
            "user_inputs_schema": {"type": "object", "properties": {"podcast_feeds": {"type": "array", "items": {"type": "string"}, "title": "Podcast RSS Feeds"}, "youtube_channels": {"type": "array", "items": {"type": "string"}, "title": "YouTube Channels"}}},
            "collection_config": {"tool": "httpx"},
        },
        {
            "subject_type": T, "category_key": "topic_newsletters", "category_name": "Newsletters",
            "category_group": "web", "default_enabled": False, "default_frequency_minutes": 1440,
            "collection_tool": "feedparser", "priority": 12,
            "description": "Monitor newsletter archives via RSS — high-signal analyst content.",
            "signal_instructions": "Monitor newsletter archives via RSS. Analyst and industry observer content is high-signal.",
            "user_inputs_schema": {"type": "object", "properties": {"newsletter_feeds": {"type": "array", "items": {"type": "string"}, "title": "Newsletter RSS Feeds"}}},
            "collection_config": {"tool": "feedparser", "max_entries": 20},
        },
    ]


PLAYBOOK_TEMPLATE_DEFAULTS: list[dict] = (
    _company_templates() + _product_templates() +
    _service_templates() + _topic_templates()
)
