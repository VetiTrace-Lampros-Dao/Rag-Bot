# Dual-Fingerprint Approach

VeriTrace identifies and tracks content using two complementary fingerprinting techniques: cryptographic hashing (SHA-256) and perceptual hashing (pHash). Each serves a distinct purpose, and together they provide comprehensive duplicate and near-duplicate detection.

## SHA-256 Cryptographic Hash

SHA-256 produces a fixed 256-bit cryptographic hash of the raw file bytes. The algorithm is deterministic — the same input always yields the same output — and it exhibits the avalanche effect, meaning any change to the input, even a single pixel or flipped bit, produces a completely different hash. There is no concept of "closeness" between two SHA-256 values; they either match exactly or they do not.

This property makes SHA-256 ideal for exact-match deduplication. If two files produce the same SHA-256 hash, they are byte-for-byte identical. The check is instantaneous and computationally inexpensive, which is why VeriTrace uses it as the first line of defence when content is submitted for verification.

## Perceptual Hash (pHash)

Perceptual hashing works on an entirely different principle. Rather than hashing raw bytes, pHash analyzes the visual or structural content of a media file — its luminance patterns, frequency components, and spatial layout — and distills that analysis into a compact 64-bit integer fingerprint.

The key advantage of pHash is resilience to minor visual modifications. Resizing, recompression, slight color shifts, format conversion, and minor cropping all produce very similar pHash values. Similarity between two perceptual hashes is measured using Hamming distance, which counts the number of differing bits between the two 64-bit values. A low Hamming distance indicates high visual similarity; a distance of zero means the visual structures are identical.

## Why Both Are Needed

VeriTrace uses SHA-256 and pHash together because they cover complementary attack surfaces. SHA-256 catches exact copies instantly and with zero ambiguity. However, it is trivially defeated by any modification — even re-saving an image at a different compression level changes every byte. Perceptual hashing fills this gap by catching near-duplicates and derivatives that have been visually modified but remain recognizably similar. The combination ensures that both verbatim reposts and lightly edited variants are detected during content verification.
