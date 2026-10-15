# Free public demo deployment

This setup is for a student-project demo. It uses Render for the FastAPI site, Supabase for PostgreSQL, and Gemini's free API tier for AI replies. The free tiers can sleep, pause, or hit usage limits, so first requests may be slow and the service is not suitable for a business that needs guaranteed uptime or support for sensitive customer data.

## 1. Put the project in a GitHub repository

Push the project source to a repository you control. The `.gitignore` excludes local `.env` files, the virtual environment, database files, and logs. Never upload API keys, JWT secrets, `.env.development`, or `.env.production`.

## 2. Create the database on Supabase

1. Create a Supabase project and save its database password somewhere private.
2. Click **Connect**, select **Session pooler**, and copy the host and username from its connection details. Use port `5432` and database `postgres`.
3. The host and username are project-specific. Do not copy them from an example or post the password publicly.

The free deployment disables the OpenAI-dependent long-term memory feature. Supabase’s free plan can pause projects after a week of low activity. It currently includes a 500 MB database quota; check the [Supabase free plan limits](https://supabase.com/pricing) before publishing. The [Supabase connection guide](https://supabase.com/docs/guides/database/connecting-to-postgres) explains its Session Pooler connection details.

## 3. Deploy the Render Blueprint

1. Push the code, including `render.yaml`, to GitHub.
2. In Render, create a new **Blueprint** and connect that repository.
3. Create a Gemini API key in [Google AI Studio](https://aistudio.google.com/apikey).
4. Render reads `render.yaml`. When prompted, enter `GEMINI_API_KEY`, `POSTGRES_HOST`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` as secret values. Use the Supabase Session Pooler host and username. The blueprint generates the JWT secret and sets the remaining database values.
5. Deploy. Render builds the Docker image and serves the frontend and API from one public URL. Open that URL for the site and append `/docs` for the API explorer.

The Render free web service spins down after 15 minutes without traffic and may take about a minute to wake up. Do not create a Render free PostgreSQL database for this project: free Render databases expire after 30 days. See [Render's free instance limits](https://render.com/docs/free).

## 4. AI provider and public usage

The deployment blueprint uses Gemini's [OpenAI-compatible endpoint](https://ai.google.dev/gemini-api/docs/openai) and `gemini-3.8-flash`; Google currently lists free input and output for this model in its [pricing](https://ai.google.dev/gemini-api/docs/pricing), subject to free-tier limits. Google says free-tier content may be used to improve its products. This option is for a demo with fictional, non-sensitive questions—not real customer records. Quotas and model availability can change. If you use OpenAI instead, set `LLM_PROVIDER=openai`, provide `OPENAI_API_KEY`, and account for API charges. Never post provider keys in GitHub, screenshots, or chat.

This demo is not connected to a real company’s orders, payment system, ticket queue, or verified support knowledge base. Tell visitors not to enter personal, account, or payment details. Use fictional/demo questions until those integrations and privacy controls are built.
