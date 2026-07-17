# Verify Endpoint

The VeriTrace `/verify` endpoint is the primary interface for checking content against the registry. It accepts a file or content identifier and returns a comprehensive report on both exact and similar matches found in the system.

## Response Shape
The endpoint returns a structured JSON response designed to provide immediate clarity on the content's status. The core structure includes two main fields:

### `exact_match`
This is a nullable field. If the exact SHA-256 fingerprint of the queried file exists in the registry, this field will be populated with a dictionary containing the registered content's metadata (e.g., `content_id`, `owner`, `timestamp`). If no exact duplicate is found, this field will be `null`.

### `similar_matches`
This field contains an array of objects representing content that falls within the acceptable perceptual hashing threshold (Hamming distance <= 40). 
- **Ranked by Similarity**: The array is ranked in descending order based on the similarity percentage, meaning the closest visual matches are surfaced at the very top of the list.
- **Comprehensive Results**: The endpoint does not just return the single closest match; it surfaces *all* similar matches found in the registry that meet the threshold criteria. This provides a complete picture of the content's provenance or potential infringement across the entire dataset.
