# Hand-verification sheet — pass1

20 apps, 120 rows. Strata: {'well_known': 10, 'suspect': 10, 'clean': 0}.

Mark in `sample_sheet.json`: set one of `correct` / `incorrect` / `partial` to true per row and fill `marked_by`.

`suggested` is the adversarial pass's opinion with the line it found — useful as a starting point, not ground truth. Overrule it freely.

## 1. Salesforce  _(CRM and Sales, well_known)_

Evidence URLs:
- https://developer.salesforce.com
- https://www.salesforce.com/in/partners/

**auth.method** → `"unknown"`
- judge: **yes** (marketing)
- line: "Build with React on Salesforce: Multi-Framework Is Now GA. Ship production-ready React apps natively on Salesforce — with authentication, security, and governance built in."
- record says: The provided text mentions built-in authentication for React apps on Salesforce but does not explicitly specify the authentication protocol (such as OAuth2 or API keys) used for the public REST APIs.

**access.tier** → `"self_serve"`
- judge: **partial** (marketing)
- line: "Sign up now"
- problem: Self‑serve access requires access‑docs showing how to obtain credentials; only marketing copy is present.
- record says: Developers can sign up for a free Salesforce Developer Edition directly from the developer portal.

**api_surface** → `{"rest": true, "graphql": null, "webhooks": null, "sdks": ["Data 360 Code Extension SDK"], "notes": "The text explicitly mentions the Salesforce REST API, Marketing Cloud REST and SOAP APIs, B2C Commerce API, Metadata AP…`
- judge: **partial** (usage_docs)
- line: "Salesforce REST API Integrate Salesforce data into apps and perform complex operations on a large scale. B2C Commerce API Ensure omnichannel flexibility by using a headless API to build custom apps, from full storefronts to merchant tools. "
- problem: Only REST, B2C Commerce, Marketing Cloud (REST & SOAP) and Metadata APIs are mentioned; GraphQL, webhooks, and the Data 360 Code Extension SDK are not covered in this line.
- record says: The text explicitly mentions the Salesforce REST API, Marketing Cloud REST and SOAP APIs, B2C Commerce API, Metadata API, and the Data 360 Code Extension SDK.

**mcp.exists** → `true`
- judge: **yes** (marketing)
- line: "Expose Custom Apex as a Hosted MCP Tool for Agents ... allowing AI agents like Claude or Cursor to discover and invoke your business intelligence directly via the Model Context Protocol."
- record says: Salesforce supports Model Context Protocol (MCP). Developers can expose custom Apex logic as Hosted MCP tools, and connect third-party MCP servers directly to Agentforce or Slack.

**buildability.verdict** → `"easy"`
- judge: **partial** (marketing)
- line: "Start for free"
- problem: The line indicates a free edition but does not directly address how easy it is to build with the platform.
- record says: Salesforce offers a free Developer Edition that developers can sign up for instantly, providing access to the Salesforce REST API and hosted MCP tools.

**evidence_supports_claims** → `[{"url": "https://developer.salesforce.com", "claim": "Mentions the Salesforce REST API, free Developer Edition signup, Data 360 Code Extension SDK, and support for Model Context Protocol (MCP) hosted servers and tools."…`
- judge: **yes** (marketing)
- line: "Salesforce REST API ... Extend Data 360 with Code Extension ... using the Data 360 Code Extension SDK ... New in Salesforce Developer Edition: ... Hosted MCP Servers – all free."

## 3. Pipedrive  _(CRM and Sales, suspect)_

Evidence URLs:
- https://developers.pipedrive.com/
- https://developers.pipedrive.com/docs/api/v1

**auth.method** → `"api_key"`
- judge: **yes** (access_docs)
- line: "The API is stateless – all requests are validated against an API token. The API token can be obtained manually from the Pipedrive app."
- record says: The stateless API is validated against an API token obtained manually from the Pipedrive app.

**access.tier** → `"self_serve"`
- judge: **yes** (access_docs)
- line: "Sign up for a Sandbox Account today to begin experimenting and developing in a risk free environment."
- record says: Developers can obtain an API token manually from the Pipedrive app and sign up for a sandbox account.

**api_surface** → `{"rest": true, "graphql": null, "webhooks": true, "sdks": ["Node.js", "PHP"], "notes": "Supports a RESTful API with OpenAPI 3 specifications, webhooks, and official Node.js and PHP client libraries."}`
- judge: **partial** (usage_docs)
- line: "We offer two official Pipedrive API client libraries: Node.js and PHP."
- problem: Claim also includes RESTful API and webhooks, which are not covered by this line.
- record says: Supports a RESTful API with OpenAPI 3 specifications, webhooks, and official Node.js and PHP client libraries.

**mcp.exists** → `null`
- judge: **no** (none)
- problem: No claim provided to verify.

**buildability.verdict** → `"easy"`
- judge: **yes** (usage_docs)
- line: "Pipedrive is an amazing tool! Their developer API, well-documented API reference page and easy use of webhooks allow developers to easily build solutions in the Pipedrive Developer Platform."
- record says: Self-service credential generation (API token obtained manually from the app/sandbox) combined with a well-documented RESTful API and official SDKs makes it easy for outside developers to build.

**evidence_supports_claims** → `[{"url": "https://developers.pipedrive.com/", "claim": "Mentions building integrations with the API and easy use of webhooks."}, {"url": "https://developers.pipedrive.com/docs/api/v1", "claim": "Describes the RESTful Pip…`
- judge: **partial** (marketing)
- line: "Easily build integrations with our API and developer platform to reach over 100,000 companies through the Pipedrive Marketplace."
- problem: Does not mention the RESTful API token validation claim.

## 12. Intercom  _(Support and Helpdesk, well_known)_

Evidence URLs:
- https://developers.intercom.com/docs
- https://developers.intercom.com/docs
- https://developers.intercom.com/docs

**auth.method** → `"oauth2"`
- judge: **yes** (usage_docs)
- line: "Public apps (sometimes referred to as integrations) are apps that are available for any customer to install. These apps have access to other peoples' Intercom data, which means there are specific requirements in order to publish them, such "
- record says: Public apps require setting up OAuth, while private apps can use an Access Token.

**access.tier** → `"self_serve"`
- judge: **yes** (access_docs)
- line: "sign up here to create your free account. This will give you access to your Developer Hub."
- record says: Developers can sign up for a free account to create a development workspace and access the Developer Hub.

**api_surface** → `{"rest": true, "graphql": null, "webhooks": true, "sdks": null, "notes": "The platform provides REST APIs, webhooks, and SDKs (including mobile SDKs and Canvas Kit)."}`
- judge: **partial** (usage_docs)
- line: "If you aren't able to find an existing app that solves the problem you're facing, you can build your own using our REST APIs and Canvas Kit framework."
- problem: The quoted line mentions REST APIs and SDKs (Canvas Kit) but does not mention webhooks, which are also claimed.
- record says: The platform provides REST APIs, webhooks, and SDKs (including mobile SDKs and Canvas Kit).

**mcp.exists** → `null`
- judge: **no** (none)
- problem: No information about an MCP (Marketplace) is present in the provided text.

**buildability.verdict** → `"moderate"`
- judge: **no** (none)
- problem: The text does not provide an overall assessment of buildability difficulty (e.g., 'moderate').
- record says: Self-serve developer accounts are available to obtain credentials and test integrations, but public apps require OAuth configuration and submission to the Intercom team for review.

**evidence_supports_claims** → `[{"url": "https://developers.intercom.com/docs", "claim": "Public apps require setting up OAuth and submitting to the Intercom team for review, whereas private apps can use an Access Token without review."}, {"url": "htt…`
- judge: **no** (none)
- problem: The specific claim statements are not directly quoted in the provided text; while related information exists, no single line verifies each listed claim.

## 19. Gorgias  _(Support and Helpdesk, suspect)_

Evidence URLs:
- https://developers.gorgias.com/
- https://www.gorgias.com/onboarding

**auth.method** → `"unknown"`
- judge: **no** (none)
- problem: No information about authentication method in the provided text.

**access.tier** → `"unknown"`
- judge: **partial** (access_docs)
- line: "Sign up for our Developer Portal to start our partnership. This step is required only if you plan to build a Public app."
- problem: Access tier is described (public apps require sign‑up/approval, private apps are self‑serve), so claim of unknown is incorrect.

**api_surface** → `{"rest": null, "graphql": null, "webhooks": null, "sdks": null, "notes": "The pages mention an open API and API documentation exist, but do not provide specific substantive details about REST, GraphQL, webhooks, or SDKs.…`
- judge: **yes** (marketing)
- line: "Refer to our API documentation to find all the information you need."
- record says: The pages mention an open API and API documentation exist, but do not provide specific substantive details about REST, GraphQL, webhooks, or SDKs.

**mcp.exists** → `null`
- judge: **no** (none)
- problem: No mention of MCP in the provided text.

**buildability.verdict** → `"unknown"`
- judge: **partial** (marketing)
- line: "Open API to build and customize integrations"
- problem: Text indicates that building integrations is possible via an open API, so claim of unknown is incorrect.
- record says: The fetched pages mention an open API and developer documentation, but do not specify authentication mechanisms or how to obtain credentials.

**evidence_supports_claims** → `[{"url": "https://developers.gorgias.com/", "claim": "Refers to API documentation and developer portal for building private or public apps."}, {"url": "https://www.gorgias.com/onboarding", "claim": "Mentions an open API …`
- judge: **no** (none)

## 21. Slack  _(Communications and Messaging, well_known)_

Evidence URLs:
- https://docs.slack.dev/apis/web-api/
- https://api.slack.com/apps
- https://docs.slack.dev/authentication/
- https://docs.slack.dev/

**auth.method** → `"oauth2"`
- judge: **yes** (usage_docs)
- line: "OAuth 2.0 : Learn how to use OAuth 2.0 to securely authenticate users and request access tokens."
- record says: Slack uses OAuth 2.0 to securely authenticate users and request access tokens (user, bot, and app tokens), which are passed as Bearer tokens in the Authorization header.

**access.tier** → `"self_serve"`
- judge: **yes** (access_docs)
- line: "You'll need to sign in to your Slack account to create an application."
- record says: Developers can sign in to their Slack account to create an application, or use the Slack CLI to log in and create a project.

**api_surface** → `{"rest": false, "graphql": null, "webhooks": null, "sdks": ["Java Slack SDK", "Node Slack SDK", "Python Slack SDK", "Bolt for Java", "Bolt for JavaScript", "Bolt for Python"], "notes": "The Web API is a collection of HTT…`
- judge: **no** (none)
- record says: The Web API is a collection of HTTP RPC-style methods rather than a REST API, though it uses HTTP foundations. Official SDKs and Bolt frameworks are provided for Java, JavaScript/Node, and Python.

**mcp.exists** → `null`
- judge: **no** (none)

**buildability.verdict** → `"easy"`
- judge: **no** (none)
- record says: Slack offers self-serve access where developers can sign in and create apps immediately. The API is well-documented with multiple official SDKs and a CLI to streamline development.

**evidence_supports_claims** → `[{"url": "https://docs.slack.dev/apis/web-api/", "claim": "The Slack Web API is an HTTP RPC-style interface (not REST) that accepts OAuth 2.0 Bearer tokens."}, {"url": "https://api.slack.com/apps", "claim": "Developers c…`
- judge: **no** (none)

## 28. WhatsApp Business  _(Communications and Messaging, suspect)_

Evidence URLs:
- https://developers.facebook.com/documentation/business-messaging/whatsapp/overview
- https://developers.facebook.com/documentation/business-messaging/whatsapp/about-the-platform
- https://developers.facebook.com/

**auth.method** → `"api_key"`
- judge: **partial** (usage_docs)
- line: ""Authorization": "Bearer <ACCESS_TOKEN>","
- problem: The claim says authentication uses an API key, but the text shows bearer token authentication.
- record says: Uses bearer access tokens (system tokens or business tokens) passed in the Authorization header.

**access.tier** → `"mixed"`
- judge: **partial** (access_docs)
- line: "Onboard customers: Learn how to build Embedded Signup; a flow to onboard customers directly from your website."
- problem: The text mentions self‑serve embedded signup and partner resources, but does not describe the mixed tier details such as business verification or credit‑line setup claimed.
- record says: Developers can sign up and use developer tools/embedded signup, but certain partner solutions and advanced onboarding require business verification, solution partner processes, or credit line setup.

**api_surface** → `{"rest": true, "graphql": false, "webhooks": true, "sdks": ["Python", "JavaScript"], "notes": "Uses HTTP REST requests built on the Graph API and delivers JSON payloads via webhooks."}`
- judge: **partial** (marketing)
- line: "Select language Python JavaScript cURL"
- problem: The line confirms SDK language options and implies REST/HTTP usage, but the text does not explicitly state that GraphQL is unsupported nor does it list all REST capabilities; therefore the full claim is not completely verified.
- record says: Uses HTTP REST requests built on the Graph API and delivers JSON payloads via webhooks.

**mcp.exists** → `true`
- judge: **yes** (marketing)
- line: "Announcing WhatsApp Business Tools MCP: Set up and manage WhatsApp business from your AI agent"
- record says: WhatsApp Business Tools MCP allows setting up and managing WhatsApp business from an AI agent.

**buildability.verdict** → `"moderate"`
- judge: **no** (none)
- problem: The text provides no statement about the overall difficulty (e.g., "moderate") of building with the platform.
- record says: Access requires setting up Meta developer accounts and obtaining system or business access tokens via embedded signup flows, while the Cloud API and webhooks are thoroughly documented.

**evidence_supports_claims** → `[{"url": "https://developers.facebook.com/documentation/business-messaging/whatsapp/overview", "claim": "The WhatsApp Business Platform provides Cloud API, Marketing Messages API, and Business Management API for messagin…`
- judge: **partial** (marketing)
- line: "Cloud API ... Marketing Messages API for WhatsApp ... Business Management API"
- problem: The quoted line supports the first sub‑claim about the three APIs, but does not address the HTTP/Graph API/webhooks claim nor the MCP announcement, so the bundled claim is only partially covered.

## 33. LinkedIn Ads  _(Marketing, Ads, Email and Social, suspect)_

Evidence URLs:
- https://learn.microsoft.com/en-us/linkedin/shared/authentication/authentication
- https://learn.microsoft.com/en-us/linkedin/marketing/quick-start?view=li-lms-2026-09
- https://learn.microsoft.com/en-us/linkedin/marketing/quick-start?view=li-lms-2026-09

**auth.method** → `"oauth2"`
- judge: **yes** (usage_docs)
- line: "The LinkedIn API uses OAuth 2.0 for member (user) authorization and API authentication."
- record says: Uses OAuth 2.0 with member authorization (3-legged OAuth code flow) for Marketing APIs.

**access.tier** → `"mixed"`
- judge: **no** (none)
- problem: No evidence about tier creation or upgrade process.
- record says: Developers can create a developer application in the Developer Portal to get development tier access, but upgrading to Standard tier requires application review forms and a video demonstration.

**api_surface** → `{"rest": true, "graphql": null, "webhooks": null, "sdks": null, "notes": "Offers REST APIs for campaign management, reporting, community management, and lead sync."}`
- judge: **partial** (marketing)
- line: "The platform offers APIs to create LinkedIn marketing campaigns, to report campaign performance, to manage leads, and to grow a company Page."
- problem: Does not explicitly state that the APIs are REST.
- record says: Offers REST APIs for campaign management, reporting, community management, and lead sync.

**mcp.exists** → `null`
- judge: **no** (none)
- problem: No mention of MCP in the provided text.

**buildability.verdict** → `"moderate"`
- judge: **no** (none)
- problem: Text does not confirm self‑serve developer portal access or tier‑upgrade requirements.
- record says: Self-serve development access is available via the Developer Portal with OAuth 2.0 authentication, but APIs require application approval and tier upgrade processes (such as submitting review forms or demonstration videos) for standard acces

**evidence_supports_claims** → `[{"url": "https://learn.microsoft.com/en-us/linkedin/shared/authentication/authentication", "claim": "The LinkedIn API uses OAuth 2.0 for member authorization and API authentication."}, {"url": "https://learn.microsoft.c…`
- judge: **no** (none)

## 34. GoHighLevel  _(Marketing, Ads, Email and Social, suspect)_

Evidence URLs:
- https://developers.gohighlevel.com

**auth.method** → `"oauth2"`
- judge: **yes** (marketing)
- line: "We now have an OAuth based API"
- record says: API 2.0 uses an OAuth based API.

**access.tier** → `"unknown"`
- judge: **no** (none)
- problem: no information on how developers obtain credentials or access tier
- record says: The pages mention an OAuth based API 2.0 and API 1.0 docs, but do not provide explicit details on how a developer initially registers or obtains credentials.

**api_surface** → `{"rest": true, "graphql": null, "webhooks": null, "sdks": null, "notes": "Mentions Public API endpoints, API 1.0, and API 2.0."}`
- judge: **yes** (marketing)
- line: "Your go-to resource for our Public API endpoints and documentation."
- record says: Mentions Public API endpoints, API 1.0, and API 2.0.

**mcp.exists** → `null`
- judge: **no** (none)
- problem: no mention of MCP in the provided text

**buildability.verdict** → `"unknown"`
- judge: **no** (none)
- problem: no information on developer buildability or access
- record says: The pages document APIs and OAuth auth, but do not state how developers obtain access credentials.

**evidence_supports_claims** → `[{"url": "https://developers.gohighlevel.com", "claim": "The platform offers API 2.0 Docs using an OAuth based API and API 1.0 Docs for public endpoints."}]`
- judge: **partial** (marketing)
- line: "We now have an OAuth based API"
- problem: does not mention API 1.0 Docs for public endpoints in the same sentence

## 38. Pinterest  _(Marketing, Ads, Email and Social, well_known)_

Evidence URLs:
- https://developers.pinterest.com
- https://developers.pinterest.com/docs/getting-started/connect-app/
- https://developers.pinterest.com/docs/getting-started/connect-app/
- https://developer.pinterest.com/

**auth.method** → `"oauth2"`
- judge: **yes** (usage_docs)
- line: "Build a working authentication flow based on OAuth 2"
- record says: Build a working authentication flow based on OAuth 2. Product limited tokens are also available for testing once approved for trial access.

**access.tier** → `"gated"`
- judge: **partial** (access_docs)
- line: "Application requests are reviewed each business day."
- problem: Claim also mentions needing a business account and accepting developer terms, which are not covered by this line.
- record says: Requires creating a business account, accepting developer terms, and submitting a request for trial access which is reviewed each business day.

**api_surface** → `{"rest": null, "graphql": null, "webhooks": null, "sdks": ["Python"], "notes": "The API supports managing content, ads, shopping catalogs, conversions, and analytics. A Python SDK is mentioned."}`
- judge: **partial** (usage_docs)
- line: "Python SDK : Our SDK currently offers a Python library that supports campaign management and simplifies authentication and error handling."
- problem: The claim lists multiple API capabilities (content, ads, catalogs, conversions, analytics) not demonstrated by this line; only the Python SDK is mentioned.
- record says: The API supports managing content, ads, shopping catalogs, conversions, and analytics. A Python SDK is mentioned.

**mcp.exists** → `true`
- judge: **yes** (marketing)
- line: "Pinterest MCP is on the way"
- record says: Pinterest MCP is mentioned as on the way / build faster with the Pinterest MCP.

**buildability.verdict** → `"moderate"`
- judge: **no** (none)
- problem: The text does not provide an overall buildability assessment such as 'moderate'.
- record says: Access requires manual application review for trial access (gated tier), but once approved, authentication uses standard OAuth 2 and there is documentation and a Python SDK.

**evidence_supports_claims** → `[{"url": "https://developers.pinterest.com", "claim": "Pinterest API provides use cases for tracking conversions, creating content, building and managing ads, managing product catalogs, and analyzing Pinterest data."}, {…`
- judge: **no** (none)
- problem: The claim aggregates multiple external URL statements; the provided text does not verify each URL's specific claim.

## 40. SendGrid  _(Marketing, Ads, Email and Social, well_known)_

Evidence URLs:
- https://www.twilio.com/docs/sendgrid/api-reference
- https://www.twilio.com/docs/sendgrid/ui/account-and-settings/api-keys
- https://www.twilio.com/docs/sendgrid

**auth.method** → `"api_key"`
- judge: **yes** (usage_docs)
- line: "This section stores your key in a local environment variable named SENDGRID_API_KEY"
- record says: Authentication uses Application Programming Interface (API) keys generated in the console and stored in an environment variable named SENDGRID_API_KEY.

**access.tier** → `"self_serve"`
- judge: **yes** (access_docs)
- line: "Go to Settings > API Keys. The API Keys page displays your current API keys with the following parameters:"
- record says: Developers can create an account and generate API keys directly in Settings > API Keys without contacting sales.

**api_surface** → `{"rest": true, "graphql": false, "webhooks": null, "sdks": ["C#", "Go", "Java", "Node.js", "PHP", "Python", "Ruby"], "notes": "The SendGrid v3 Web API provides a REST interface accompanied by open-source SDKs in multiple…`
- judge: **partial** (marketing)
- line: "The SendGrid v3 Web API provides a REST interface to send email at scale"
- problem: The claim also asserts the presence of SDKs for multiple languages and that GraphQL is not offered; the quoted line only confirms the REST interface.
- record says: The SendGrid v3 Web API provides a REST interface accompanied by open-source SDKs in multiple programming languages.

**mcp.exists** → `null`
- judge: **yes** (none)

**buildability.verdict** → `"easy"`
- judge: **partial** (marketing)
- line: "Use up-to-date documentation to quickly integrate and send with our APIs."
- problem: The text does not explicitly state that building is "easy"; it only suggests documentation and examples are available.
- record says: Self-serve API keys can be generated immediately in the dashboard, and the REST API is fully documented with official code examples and SDKs in multiple languages.

**evidence_supports_claims** → `[{"url": "https://www.twilio.com/docs/sendgrid/api-reference", "claim": "The SendGrid v3 Web API provides a REST interface to send email at scale."}, {"url": "https://www.twilio.com/docs/sendgrid/ui/account-and-settings/…`
- judge: **yes** (marketing)
- line: "The SendGrid v3 Web API provides a REST interface to send email at scale"

## 42. WooCommerce  _(Ecommerce, well_known)_

Evidence URLs:
- https://woocommerce.com/document/woocommerce-rest-api/
- https://woocommerce.github.io/woocommerce-rest-api-docs/

**auth.method** → `"api_key"`
- judge: **yes** (access_docs)
- line: "After generating the key, the screen displays your Consumer Key, Consumer Secret, a QR Code, and a Revoke Key link."
- record says: Integrations use Consumer Key and Consumer Secret credentials generated in the WooCommerce merchant dashboard.

**access.tier** → `"self_serve"`
- judge: **yes** (access_docs)
- line: "To create or manage keys for a specific WordPress user: Go to WooCommerce > Settings > Advanced > REST API Select Create an API key or Add Key."
- record says: Merchants can generate REST API keys directly from their own WordPress dashboard under WooCommerce > Settings > Advanced > REST API without approval.

**api_surface** → `{"rest": true, "graphql": null, "webhooks": true, "sdks": null, "notes": "The platform exposes a REST API (integrated via WordPress REST API) and supports webhooks."}`
- judge: **yes** (marketing)
- line: "Webhooks configured to use the legacy REST API also stop working unless you install this plugin."
- record says: The platform exposes a REST API (integrated via WordPress REST API) and supports webhooks.

**mcp.exists** → `false`
- judge: **partial** (marketing)
- line: "Call for Testing: WooCommerce MCP Beta"
- problem: Only a beta is mentioned; no explicit statement that no production server exists.
- record says: There is a blog mention of testing a WooCommerce MCP Beta, but no production Model Context Protocol server is documented for public developer use.

**buildability.verdict** → `"easy"`
- judge: **partial** (access_docs)
- line: "To create or manage keys for a specific WordPress user: Go to WooCommerce > Settings > Advanced > REST API Select Create an API key or Add Key."
- problem: Line shows self‑serve key generation but does not directly address overall ease of building integrations.
- record says: Credentials are self-serve via the WooCommerce store dashboard, and the REST API is fully documented with standard endpoints and error handling.

**evidence_supports_claims** → `[{"url": "https://woocommerce.com/document/woocommerce-rest-api/", "claim": "Explains generating API keys with Consumer Key and Consumer Secret in the WooCommerce dashboard."}, {"url": "https://woocommerce.github.io/wooc…`
- judge: **no** (none)

## 45. Magento (Adobe Commerce)  _(Ecommerce, suspect)_

Evidence URLs:
- https://developer.adobe.com/commerce/
- https://developer.adobe.com/commerce/extensibility/
- https://developer.adobe.com/commerce/extensibility/webhooks/
- https://developer.adobe.com/commerce/extensibility/admin-ui-sdk/
- https://developer.adobe.com/graphql-mesh-gateway/

**auth.method** → `"other"`
- judge: **partial** (marketing)
- line: "Commerce SDKs and libraries provide reusable patterns for authentication, configuration, event handling, and Commerce integration, including the Admin UI SDK and OOPE modules."
- problem: does not mention Adobe Identity Management Service (IMS) as used for authentication
- record says: Authentication uses Adobe Identity Management Service (IMS) or reusable patterns provided by Commerce SDKs and libraries.

**access.tier** → `"unknown"`
- judge: **no** (none)
- problem: no information about sign‑up or credential acquisition flow
- record says: The fetched developer documentation describes extensibility and building apps, but does not explicitly detail the sign-up or credential acquisition flow for a first-time unaffiliated developer.

**api_surface** → `{"rest": true, "graphql": true, "webhooks": true, "sdks": ["Admin UI SDK"], "notes": "Supports REST endpoints, GraphQL (via API Mesh), webhooks, events, and App Builder SDKs."}`
- judge: **no** (none)
- record says: Supports REST endpoints, GraphQL (via API Mesh), webhooks, events, and App Builder SDKs.

**mcp.exists** → `null`
- judge: **no** (none)
- record says: The pages do not mention the Model Context Protocol.

**buildability.verdict** → `"moderate"`
- judge: **no** (none)
- record says: Extensive developer documentation and tools (App Builder, SDKs) exist, but access and credential provisioning details are not fully specified on these pages.

**evidence_supports_claims** → `[{"url": "https://developer.adobe.com/commerce/", "claim": "Adobe provides developers with software, tools, and services to customize and extend Adobe Commerce."}, {"url": "https://developer.adobe.com/commerce/extensibil…`
- judge: **no** (none)

## 53. Ahrefs  _(Data, SEO and Scraping, suspect)_

Evidence URLs:
- https://docs.ahrefs.com
- https://docs.ahrefs.com/en/ahrefs-connect/docs/oauth-guide
- https://docs.ahrefs.com/en/api/docs/introduction
- https://docs.ahrefs.com/en/ahrefs-connect/docs/how-to-apply
- https://docs.ahrefs.com/en/api/docs/api-keys-creation-and-management

**auth.method** → `"api_key"`
- judge: **partial** (usage_docs)
- line: "To send requests to Ahrefs API, you'll need an API key."
- problem: The text does not specify that the API key is sent in the Authorization header as a Bearer token, and does not mention OAuth 2.0 Authorization Code Flow with PKCE.
- record says: API requests require an API key sent in the Authorization header as a Bearer token (Authorization: Bearer YOUR_API_KEY). Ahrefs Connect also uses OAuth 2.0 Authorization Code Flow with PKCE.

**access.tier** → `"mixed"`
- judge: **partial** (marketing)
- line: "Ahrefs API is available on eligible paid plans. On all other plans, you'll still have access to a limited set of free test queries."
- problem: No evidence in the text about needing to submit an application form to join the Ahrefs Connect integration program.
- record says: Ahrefs API is available on eligible paid plans and includes limited free test queries, but joining the Ahrefs Connect integration program requires submitting an application form.

**api_surface** → `{"rest": true, "graphql": false, "webhooks": false, "sdks": null, "notes": "Provides a REST API (API v3) with an OpenAPI-compatible specification."}`
- judge: **yes** (marketing)
- line: "REST API ... OpenAPI spec Full machine-readable spec for every endpoint."
- record says: Provides a REST API (API v3) with an OpenAPI-compatible specification.

**mcp.exists** → `true`
- judge: **yes** (marketing)
- line: "MCP Connect your Ahrefs data to AI assistants and agents to enhance their answers with real marketing insights."
- record says: Ahrefs documents Model Context Protocol (MCP) support for connecting Ahrefs data to AI assistants and agents such as Claude and ChatGPT.

**buildability.verdict** → `"moderate"`
- judge: **partial** (access_docs)
- line: "To send requests to Ahrefs API, you'll need an API key. Only workspace owners and admins can create and manage API keys. This can be done in Account settings / API keys."
- problem: The text does not mention the application review and approval process required for third‑party apps via Ahrefs Connect.
- record says: Standard API usage requires an eligible paid plan and an API key from account settings, while third-party apps via Ahrefs Connect require an application review and approval process.

**evidence_supports_claims** → `[{"url": "https://docs.ahrefs.com", "claim": "Ahrefs provides APIs and developer tools like REST API and MCP."}, {"url": "https://docs.ahrefs.com/en/ahrefs-connect/docs/oauth-guide", "claim": "Ahrefs Connect uses OAuth 2…`
- judge: **no** (none)
- problem: The claim aggregates multiple URL‑specific statements, but no single line in the provided text confirms all of them together.

## 62. Vercel  _(Developer, Infra and Data platforms, well_known)_

Evidence URLs:
- https://vercel.com/docs/rest-api
- https://vercel.com/docs/rest-api
- https://vercel.com/docs

**auth.method** → `"api_key"`
- judge: **yes** (usage_docs)
- line: "Vercel Access Tokens are required to authenticate and use the Vercel API. Include the token in the Authorization header: Authorization: Bearer <TOKEN>"
- record says: Vercel Access Tokens are sent via the Authorization: Bearer <TOKEN> header.

**access.tier** → `"self_serve"`
- judge: **yes** (access_docs)
- line: "Create and manage Access Tokens in your account settings"
- record says: Users can create and manage Access Tokens directly in their account settings.

**api_surface** → `{"rest": true, "graphql": null, "webhooks": true, "sdks": null, "notes": "The API is exposed as an HTTP/1 and HTTP/2 service over SSL following REST architecture."}`
- judge: **partial** (usage_docs)
- line: "The API is exposed as an HTTP/1 and HTTP/2 service over SSL. All endpoints live under the URL https://api.vercel.com and follow the REST architecture."
- problem: Webhooks are listed separately in the endpoint list but not mentioned in the same sentence as the REST architecture; the claim bundles REST and Webhooks together.
- record says: The API is exposed as an HTTP/1 and HTTP/2 service over SSL following REST architecture.

**mcp.exists** → `true`
- judge: **yes** (marketing)
- line: "Vercel MCP
Beta
Let your agent search the docs, manage projects and deployments, and query Web Analytics through the Vercel MCP server."
- record says: Vercel MCP server allows agents to search docs, manage projects and deployments, and query Web Analytics.

**buildability.verdict** → `"easy"`
- judge: **no** (none)
- problem: The text does not state that building or using the API is "easy"; it only describes credential creation and API documentation.
- record says: Self-serve credentials can be generated in account settings and the REST API is thoroughly documented.

**evidence_supports_claims** → `[{"url": "https://vercel.com/docs/rest-api", "claim": "Vercel Access Tokens are required to authenticate and use the Vercel API via Authorization Bearer header."}, {"url": "https://vercel.com/docs/rest-api", "claim": "Cr…`
- judge: **yes** (usage_docs)
- line: "Vercel Access Tokens are required to authenticate and use the Vercel API. Include the token in the Authorization header: Authorization: Bearer <TOKEN>"

## 69. Datadog  _(Developer, Infra and Data platforms, well_known)_

Evidence URLs:
- https://docs.datadoghq.com/api/latest/
- https://docs.datadoghq.com/api/latest/oauth2-client-public/register-an-oauth2-client/

**auth.method** → `"api_key"`
- judge: **partial** (usage_docs)
- line: "Authenticate to the API with an API key using the header DD-API-KEY. For some endpoints, you also need an Application key, which uses the header DD-APPLICATION-KEY."
- problem: OAuth2 dynamic client registration support not mentioned
- record says: Authenticates using an API key sent via the DD-API-KEY header, and optionally an Application key via DD-APPLICATION-KEY. OAuth2 dynamic client registration is also supported for public clients.

**access.tier** → `"unknown"`
- judge: **no** (none)
- problem: no information on how to obtain initial credentials
- record says: The pages document API endpoints and client libraries, but do not state how a first-time developer obtains initial credentials.

**api_surface** → `{"rest": true, "graphql": null, "webhooks": null, "sdks": ["java", "python", "ruby", "go", "javascript", "rust"], "notes": "Provides an HTTP REST API with official client libraries in Java, Python, Ruby, Go, JavaScript/T…`
- judge: **partial** (usage_docs)
- line: "The Datadog API is an HTTP REST API."
- problem: does not list all claimed SDK languages explicitly
- record says: Provides an HTTP REST API with official client libraries in Java, Python, Ruby, Go, JavaScript/TypeScript, and Rust.

**mcp.exists** → `null`
- judge: **no** (none)
- problem: no mention of MCP existence

**buildability.verdict** → `"unknown"`
- judge: **no** (none)
- problem: cannot determine access tier due to lack of credential acquisition info
- record says: While API documentation and client libraries are available, the pages do not describe how credentials are obtained (access tier is unknown), preventing a definitive buildability assessment.

**evidence_supports_claims** → `[{"url": "https://docs.datadoghq.com/api/latest/", "claim": "The Datadog API is an HTTP REST API, and authenticates with an API key using the header DD-API-KEY and optionally an Application key using DD-APPLICATION-KEY."…`
- judge: **no** (none)

## 72. Airtable  _(Productivity and Project Management, well_known)_

Evidence URLs:
- https://airtable.com/developers/agents
- https://airtable.com/developers/agents/mcp/tools
- https://airtable.com/developers/agents/mcp/getting-started

**auth.method** → `"oauth2"`
- judge: **yes** (marketing)
- line: "Claude ... Connects in one click via OAuth."
- record says: The MCP server supports OAuth (recommended for end-user connections with Dynamic Client Registration) and Personal Access Tokens (PATs for CLI, scripts, and server-side setups).

**access.tier** → `"self_serve"`
- judge: **partial** (marketing)
- line: "The server is available to all users on all plans."
- problem: Claim of self‑serve credential acquisition is not supported by access documentation; only marketing about availability is present.
- record says: The server is available to all users on all plans, and developers can connect via self-serve OAuth or generate Personal Access Tokens.

**api_surface** → `{"rest": null, "graphql": null, "webhooks": null, "sdks": ["@airtable/mcp-cli"], "notes": "The pages describe a Model Context Protocol (MCP) server interface for AI agents rather than a standard REST or GraphQL API surfa…`
- judge: **yes** (usage_docs)
- line: "npm install -g @airtable/mcp-cli"
- record says: The pages describe a Model Context Protocol (MCP) server interface for AI agents rather than a standard REST or GraphQL API surface.

**mcp.exists** → `true`
- judge: **yes** (marketing)
- line: "Tools exposed by Airtable's remote MCP server at https://mcp.airtable.com/mcp"
- record says: Airtable exposes a remote MCP server supporting tools for bases, fields, forms, interfaces, and automations.

**buildability.verdict** → `"easy"`
- judge: **yes** (marketing)
- line: "If you're new to Airtable, the fastest way to get started is to build something from nothing."
- record says: Self-serve access to accounts and documentation combined with standard OAuth and PAT authentication makes building integrations straightforward.

**evidence_supports_claims** → `[{"url": "https://airtable.com/developers/agents", "claim": "Airtable provides an MCP-compatible tool layer for AI agents to read, write, and query bases."}, {"url": "https://airtable.com/developers/agents/mcp/tools", "c…`
- judge: **partial** (marketing)
- line: "The server is available to all users on all plans."
- problem: No line found confirming that the MCP server supports Personal Access Tokens (PATs).

## 78. Coda  _(Productivity and Project Management, suspect)_

Evidence URLs:
- https://docs.superhuman.com/developers/apis/v1
- https://docs.superhuman.com/developers/apis/v1
- https://docs.superhuman.com/@oleg/getting-started-guide-coda-api

**auth.method** → `"unknown"`
- judge: **no** (none)
- problem: No information about authentication method in the provided text.
- record says: The provided pages do not describe how API requests are authenticated (e.g., header format or token type).

**access.tier** → `"unknown"`
- judge: **no** (none)
- problem: No information on how to obtain credentials.
- record says: The provided text mentions API documentation and guides, but does not state how a developer obtains credentials.

**api_surface** → `{"rest": true, "graphql": false, "webhooks": false, "sdks": null, "notes": "The API is described as a RESTful API. A Model Context Protocol (MCP) server is also mentioned."}`
- judge: **partial** (marketing)
- line: "The Superhuman Docs API is a RESTful API that lets you programmatically interact with data in Superhuman Docs (formerly Coda):"
- problem: No evidence regarding GraphQL or webhooks support; claim that they are false is unsupported.
- record says: The API is described as a RESTful API. A Model Context Protocol (MCP) server is also mentioned.

**mcp.exists** → `true`
- judge: **yes** (marketing)
- line: "If you plan to integrate Superhuman Docs with an AI tool, you may also want to consider using the Superhuman Docs MCP server. It's optimized for LLM usage patterns and often exposes more granular methods for accessing and modifying data."
- record says: The pages mention a Superhuman Docs MCP server optimized for LLM usage patterns.

**buildability.verdict** → `"unknown"`
- judge: **no** (none)
- problem: Insufficient information to assess buildability (no credential or authentication details).
- record says: Buildability cannot be fully determined because the pages do not explain how to obtain credentials or how to authenticate requests.

**evidence_supports_claims** → `[{"url": "https://docs.superhuman.com/developers/apis/v1", "claim": "The Superhuman Docs API is a RESTful API that lets you programmatically interact with data in Superhuman Docs (formerly Coda)."}, {"url": "https://docs…`
- judge: **no** (none)

## 81. Stripe  _(Finance and Fintech, well_known)_

Evidence URLs:
- https://docs.stripe.com/api
- https://docs.stripe.com/keys
- https://docs.stripe.com/development
- https://docs.stripe.com/api/authentication

**auth.method** → `"api_key"`
- judge: **yes** (usage_docs)
- line: "The Stripe API authenticates requests using HTTP Basic Auth."
- record says: API requests are authenticated using API keys provided via HTTP Basic Auth (with the key as the username) or via a Bearer token.

**access.tier** → `"self_serve"`
- judge: **yes** (access_docs)
- line: "create an account to load your test API keys."
- record says: Developers can create an account and obtain test and live API keys directly through the Stripe Dashboard.

**api_surface** → `{"rest": true, "graphql": false, "webhooks": true, "sdks": ["Ruby", "Python", "PHP", "Java", "Node.js", "Go", ".NET"], "notes": "The Stripe API is organized around REST and provides multiple official server-side client l…`
- judge: **partial** (marketing)
- line: "The Stripe API is organized around REST."
- problem: Only REST and SDKs are mentioned; the text does not mention GraphQL or webhooks, so the claim about GraphQL=false and webhooks=true is unsupported.
- record says: The Stripe API is organized around REST and provides multiple official server-side client libraries and a CLI.

**mcp.exists** → `true`
- judge: **yes** (marketing)
- line: "MCP Enable agents to use tools and securely take actions in your Stripe account."
- record says: Mentioned as part of agent-ready tooling and developer features.

**buildability.verdict** → `"easy"`
- judge: **no** (none)
- problem: The provided text contains no statement about the ease of building with Stripe; the claim is subjective and unsupported.
- record says: Self-service credentials are automatically available upon account creation, and the REST API is extensively documented with client libraries and a CLI.

**evidence_supports_claims** → `[{"url": "https://docs.stripe.com/api", "claim": "The Stripe API is organized around REST, uses standard HTTP verbs, and authenticates using API keys via HTTP Basic Auth or Bearer auth."}, {"url": "https://docs.stripe.co…`
- judge: **yes** (marketing)
- line: "The Stripe API is organized around REST."

## 85. iPayX  _(Finance and Fintech, suspect)_

**auth.method** → `"unknown"`
- judge: **no** (none)
- problem: No evidence in provided text.
- record says: Documentation was reachable but client-rendered; no text to read.

**access.tier** → `"unknown"`
- judge: **no** (none)
- problem: No evidence in provided text.
- record says: Documentation pages responded successfully but render their content in the browser, so no text could be extracted and the credential path could not be read. This is a limit of this pipeline, not evidence of gating. Tried: https://ipayx.ai/d

**api_surface** → `null`
- judge: **no** (none)
- problem: No claim provided.

**mcp.exists** → `null`
- judge: **no** (none)
- problem: No claim provided.

**buildability.verdict** → `"unknown"`
- judge: **no** (none)
- problem: No evidence in provided text.
- record says: Documentation exists but is client-rendered, so nothing could be read to judge buildability. Deliberately not scored as unbuildable.

**evidence_supports_claims** → `[]`
- judge: **no** (none)
- problem: No claim provided.

## 91. NotebookLM  _(AI, Research and Media-native, suspect)_

Evidence URLs:
- https://developers.google.com
- https://cloud.google.com/ai/gemini

**auth.method** → `"api_key"`
- judge: **yes** (usage_docs)
- line: "curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-5-flash:generateContent" \ -H "x-goog-api-key: $GEMINI_API_KEY" \ -H 'Content-Type: application/json' \ -X POST \ -d '{"contents":[{"parts":[{"text":"Explain how AI work"
- record says: Uses an API key passed in headers (e.g. x-goog-api-key) for the Gemini API.

**access.tier** → `"self_serve"`
- judge: **partial** (marketing)
- line: "Get your no cost Gemini API key"
- problem: self-serve claim requires access documentation; only marketing mention of a free key is present
- record says: Developers can sign up for a free Google AI Studio / Gemini API key and get started immediately.

**api_surface** → `{"rest": true, "graphql": false, "webhooks": null, "sdks": ["Python", "JavaScript", "Go", "Java"], "notes": "Provides REST endpoints and SDKs for Python, JavaScript, Go, and Java."}`
- judge: **partial** (marketing)
- line: "Python JavaScript Go Java REST"
- problem: GraphQL availability is not addressed, so claim that graphql is false cannot be confirmed
- record says: Provides REST endpoints and SDKs for Python, JavaScript, Go, and Java.

**mcp.exists** → `null`
- judge: **no** (none)
- problem: No claim provided to verify

**buildability.verdict** → `"easy"`
- judge: **partial** (marketing)
- line: "Google AI Studio is the fast path for developers, students, and researchers who want to try Gemini models and get started building with the Gemini Developer API."
- problem: Ease of building is subjective; only marketing language suggests simplicity
- record says: Self-serve credentials are available (API key) and the API is thoroughly documented with code examples across multiple languages.

**evidence_supports_claims** → `[{"url": "https://developers.google.com", "claim": "Shows curl and code snippets using the Gemini API key in headers and client libraries for Python, JavaScript, Go, and Java."}, {"url": "https://cloud.google.com/ai/gemi…`
- judge: **no** (none)
