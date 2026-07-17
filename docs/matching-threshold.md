# Matching Threshold

When evaluating potential duplicates or modified content, VeriTrace uses perceptual hashing (pHash) combined with a specific matching threshold to determine similarity. The threshold is defined as a Hamming distance.

## Hamming Distance of 40
VeriTrace uses a Hamming distance threshold of 40 for its perceptual hash comparisons. The Hamming distance measures the number of bits that differ between two perceptual hashes. A lower distance indicates higher similarity. 

## Tuned for Similarity, Not Exact Pixels
This threshold of 40 has been carefully tuned to catch near-identical or visually-similar content. It is designed to be resilient against common media modifications such as:
- Resizing, cropping, or padding
- Compression artifacts or format changes (e.g., JPEG to PNG)
- Minor color grading or brightness/contrast adjustments
- Adding small watermarks or logos

Because perceptual hashing evaluates the structural characteristics rather than exact pixel values, it will not identify completely different images as matches, but it provides a wide enough net to catch content that has been lightly manipulated to bypass exact-match filters.

## Scoring and Ranking
When a file is queried, any registered content with a Hamming distance of 40 or less is considered a "similar match". The system calculates a similarity percentage based on this distance and ranks the results in descending order, surfacing the most visually identical matches at the top of the list.
