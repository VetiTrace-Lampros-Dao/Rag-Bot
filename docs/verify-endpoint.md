# Verify Endpoint

VeriTrace exposes a set of verification endpoints under `/api/v1/verify/` that allow clients to check whether content has been previously registered. There are three endpoints, each serving a different verification strategy.

## Exact Verification

The exact verification endpoint is `GET /api/v1/verify/exact?hash=<sha256>`. It performs a SHA-256 lookup and returns a response containing the following fields: `match_found` (boolean indicating whether a match exists), `exact_match` (always true when a match is found, since this is an exact-match endpoint), `similarity` (always 100.0 for exact matches), `record` (the full content record including the creator address, registration timestamp, IPFS CID, media type, and AI tool attribution), and `on_chain_verified` (a boolean indicating whether the record was cross-checked against the blockchain smart contract).

## Fuzzy Verification

The fuzzy verification endpoint is `GET /api/v1/verify/fuzzy?phash=<uint64>`. It performs a perceptual hash similarity search using the KNN vector index and returns: `match_found` (boolean), `exact_match` (always false for fuzzy matches), `similarity` (a percentage representing how visually similar the submitted content is to the closest match), `timestamp_offset` (temporal difference information), `media_type` (the type of the matched content), `record` (the full content record), and `on_chain_verified` (blockchain cross-check result).

## Segment Verification

For video and multi-page document content, VeriTrace provides a segment verification endpoint at `POST /api/v1/verify/segments`. This endpoint accepts a JSON body containing an array of segment perceptual hashes. Rather than returning a single match, it evaluates each segment against the index and returns coverage percentages indicating what proportion of the submitted content matches previously registered material. This is particularly useful for detecting partial reuse — for instance, when a portion of a registered video appears within a longer compilation.

## No Match Response

If none of the endpoints find a match, the response contains `match_found: false` with no `record` field. The absence of a match means the content has not been previously registered in VeriTrace, but it does not make any claim about the originality or provenance of the content beyond the system's own registry.
