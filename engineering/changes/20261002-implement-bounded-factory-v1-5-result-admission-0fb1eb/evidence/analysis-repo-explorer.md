# Repository exploration

Source `b0579a390` changes 15 files (+1614/-36), adding V2 identity, an admission OpenAPI and service/API seams. It is not cherry-pickable: it regresses PR3a duplicate-key, finite-value, secret, content-type, unknown-channel and pre-copy chunk bounds, and calls two store methods that do not exist until the later persistence commit.

Adapt additively: preserve V1 and PR3a sanitization, derive or exact-compare the embedded OpenAPI schema, bind repository identity, and return explicit unavailable from the real service until persistence lands. Source OpenAPI also requires a correlation response header the runtime omits.
