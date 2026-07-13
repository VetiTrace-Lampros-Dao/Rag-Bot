# Blockchain Source of Truth

VeriTrace's canonical, immutable source of truth for all content registrations is the smart contract deployed on Arbitrum Sepolia. Every other data store in the system is derived from on-chain data and exists solely to enable fast querying and advanced matching capabilities.

## On-Chain Content Registration

When content is registered through VeriTrace, the smart contract emits a `ContentRegistered` event containing all essential metadata: the SHA-256 cryptographic hash of the content, the creator's wallet address, the perceptual hash (pHash), the registration timestamp, the IPFS Content Identifier (CID) pointing to the stored media, and an AI tool attribution label. This event is permanently recorded on the Arbitrum Sepolia blockchain and cannot be altered or deleted after confirmation.

The immutability of blockchain storage is what gives VeriTrace its trust guarantees. A content creator can prove, using only the on-chain record, that they registered a specific piece of content at a specific time. No centralized authority can retroactively modify or remove this proof.

## Off-Chain Indexing

The Go backend continuously listens to `ContentRegistered` events from the smart contract and indexes the data into three off-chain stores. PostgreSQL serves as the relational database for structured queries and metadata lookups. Redis provides a caching layer for frequently accessed records and SHA-256 lookups. Qdrant is the vector database that stores pHash vectors and enables fast K-Nearest Neighbors similarity search for fuzzy matching.

These off-chain databases are performance aids only. They exist because querying a blockchain directly for fuzzy similarity search or complex relational queries is impractical. However, they are never authoritative. If there is ever a discrepancy between what the off-chain index says and what the blockchain records show, the on-chain data wins unconditionally.

## On-Chain Cross-Verification

For critical operations, VeriTrace includes an on-chain verification step called `crossCheckBlockchain`. When a verification result is returned to a user, the system can optionally validate the off-chain record against the current smart contract state. This ensures that the cached data has not drifted from the truth due to indexing delays, bugs, or data corruption. The `on_chain_verified` field in API responses reflects whether this cross-check was performed and passed.
