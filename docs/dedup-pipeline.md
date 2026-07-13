# Dedup-First Architecture

VeriTrace follows a dedup-first pipeline design when verifying submitted content. This means the system always attempts the cheapest and fastest check before falling back to more expensive operations. The architecture is a deliberate performance optimization that minimizes unnecessary computation while maintaining comprehensive detection coverage.

## Step 1: SHA-256 Exact Match

When content is submitted for verification, the system first computes the SHA-256 cryptographic hash of the raw file bytes. This hash is then checked against the unified cross-media index, which contains SHA-256 entries for all previously registered content.

If an exact match is found, the process stops immediately. The content is confirmed as a known duplicate, and the system returns the matching record — including the original creator, registration timestamp, and blockchain reference. This lookup is extremely fast and cheap because it is a simple key-based index lookup with no approximation or scoring involved.

## Step 2: Perceptual Hash Similarity Search

Only when no exact SHA-256 match exists does the system proceed to the perceptual hash comparison stage. This step is more involved and consists of several sub-operations. First, the system computes the perceptual hash (pHash) of the submitted content, producing a 64-bit integer fingerprint that captures the visual or structural essence of the media. This 64-bit pHash is then converted into a 64-dimensional binary vector suitable for similarity search. Finally, the system performs a K-Nearest Neighbors (KNN) search in the Qdrant vector database to find registered content with similar perceptual fingerprints.

## Why This Order Matters

The dedup-first gate exists because perceptual hashing and vector search are significantly more expensive than a SHA-256 lookup. Computing a perceptual hash requires decoding the media file and performing frequency-domain analysis, which is CPU-intensive. The subsequent KNN search in the vector database involves I/O-heavy approximate nearest neighbor lookups across potentially millions of stored vectors. By placing the SHA-256 check first, VeriTrace avoids these costs entirely for any content that is a byte-for-byte duplicate of something already registered. In practice, a meaningful proportion of duplicate submissions are exact copies, so this optimization has a substantial impact on overall system throughput and resource consumption.
