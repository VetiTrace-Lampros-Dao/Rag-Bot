# The Blockchain as the Source of Truth

In the VeriTrace architecture, data integrity and provenance are paramount. To guarantee immutability, the system relies on a strict hierarchy of data storage.

## Canonical Data: The Blockchain JSON
The absolute, irrefutable source of truth for all content registrations is the blockchain JSON file maintained by the Rust (actix-web) backend. When content is registered, its metadata, SHA-256 fingerprint, and perceptual hash are immutably recorded here. Any verification or dispute resolution ultimately defers to the state recorded in this blockchain file.

## Performance Aids: SQLite and Side-Indexes
To facilitate fast querying—especially for the computationally heavy perceptual hash similarity searches—VeriTrace utilizes local databases like SQLite as side-indexes. 

It is critical to understand that **these local databases are performance aids only, and are never authoritative**. They are strictly derived from the blockchain state. If a discrepancy ever arises between the local SQLite database and the blockchain JSON file, the blockchain file is considered correct, and the local index must be rebuilt from it. This ensures that the system can offer sub-second query performance without ever compromising the cryptographic guarantees of the underlying blockchain ledger.
