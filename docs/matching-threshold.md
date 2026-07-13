# Matching Thresholds

VeriTrace uses Hamming distance to measure similarity between perceptual hashes. Because different media types exhibit different levels of natural variance in their pHash values, VeriTrace applies media-specific thresholds to balance detection sensitivity against false positive rates.

## Hamming Distance and Similarity

Hamming distance is the count of bits that differ between two 64-bit pHash values. A distance of 0 means every bit is identical, indicating that the two pieces of content have identical visual structure. A distance of 64 means every bit differs, indicating no visual relationship.

Similarity percentage is calculated from Hamming distance using the formula: ((64 - distance) / 64) × 100. For example, a Hamming distance of 0 corresponds to 100% similarity, a distance of 10 corresponds to approximately 84.4% similarity, and a distance of 32 corresponds to 50% similarity — essentially random chance for binary data.

## Image Matching Threshold

For general image matching, VeriTrace uses a Hamming distance threshold of 40 out of 64 possible bits. Content with a Hamming distance below this threshold is considered "similar" and flagged as a potential near-duplicate. This threshold was tuned through experimentation to catch near-identical and visually similar content — such as re-compressed, resized, or lightly edited versions of an original — while minimizing false positives from genuinely different images that happen to share some structural characteristics.

## Document Matching Threshold

For document matching, a much stricter threshold of 3 is used. Document perceptual hashes are inherently less variable than image hashes because documents tend to share common structural elements like text layouts, margins, and standard formatting. A looser threshold would produce an unacceptable number of false matches between unrelated documents. The tight threshold of 3 ensures that only documents with very high structural similarity are flagged.

## Video Matching Threshold

Video content receives special treatment. Rather than hashing the entire video as a single unit, VeriTrace extracts keyframes and hashes each one individually. Segment-level matching uses a per-keyframe Hamming distance threshold of 8. This stricter per-frame threshold reflects the fact that individual video frames have less variation than standalone images, and matching is aggregated across multiple keyframes to determine overall video similarity and coverage percentage.
