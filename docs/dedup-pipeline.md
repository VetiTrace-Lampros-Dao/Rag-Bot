# Dedup-First Architecture

VeriTrace employs a highly optimized, dedup-first architecture designed to gate expensive processing operations behind a fast, reliable initial check. This ensures that the system scales efficiently even as the volume of registered media grows.

## SHA-256 Cross-Media Index
The core of this architecture is the SHA-256 cross-media index. When a new file is submitted for verification or registration, the system first computes its SHA-256 hash. This hash is immediately checked against a unified, high-speed index containing the exact hashes of all previously registered content across all media types (images, videos, and documents).

## Rejecting Duplicates Early
If an exact match is found in the SHA-256 index, the system immediately flags the content as a duplicate and halts further processing. Because SHA-256 hashing and lookup are computationally inexpensive, this step resolves exact duplicates in milliseconds.

## Gating Expensive Operations
Perceptual hashing, particularly for complex media like video (which requires ffmpeg processing) or large documents (which require pdftoppm rendering), is resource-intensive. By running the SHA-256 deduplication check first, VeriTrace ensures that these expensive perceptual hashing operations are only invoked for genuinely new files or modified content that evaded the exact-match filter. This dedup-first pipeline is critical for maintaining high throughput and low latency across the platform.
