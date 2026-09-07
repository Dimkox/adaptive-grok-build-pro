# Optional env landing composition

Operator entry `compose_env_landing` reads process env (not a .env file). Unset provider keeps the shipped server on UnavailableLandingProvider. The API process still does not import httpx.

Live HTTP remains default-off and tests use MockTransport. Hosting, GitHub landing mutation, and pin swap are out of scope.
