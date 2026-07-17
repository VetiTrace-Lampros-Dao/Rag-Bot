# Dual-Fingerprint Approach

VeriTrace registers and verifies digital content (images, videos, documents) using a robust two-tiered fingerprinting methodology. This dual approach ensures both pinpoint accuracy for identical files and flexible detection for modified content.

## SHA-256 for Exact Matching
The first layer uses the SHA-256 cryptographic hash function. This provides an exact, unique fingerprint for the file's binary data. If even a single bit of the file changes, the SHA-256 hash changes completely. This allows the system to instantly and definitively recognize exact duplicates of previously registered content without any complex analysis.

## Perceptual Hashing (pHash) for Similarity
The second layer utilizes perceptual hashing (pHash). Unlike cryptographic hashes which are sensitive to any data change, perceptual hashes are designed to evaluate the visual or structural characteristics of the media. For images and videos, the pHash algorithm analyzes visual features, while for documents, a structural assessment is performed. 

This means that if an image is resized, compressed, or subjected to minor color adjustments, its pHash remains similar to the original. When combined with SHA-256, pHash enables VeriTrace to identify near-identical content and detect attempts to evade exact-match filters through minor modifications.

## Why Both Are Needed
Relying solely on exact matching (SHA-256) makes a system fragile against trivial alterations like format conversion or watermarking. Relying solely on perceptual hashing can be computationally expensive and may occasionally yield false positives on highly generic images. By using both, VeriTrace achieves the speed and certainty of exact matching alongside the resilience and comprehensive detection of similarity hashing.
