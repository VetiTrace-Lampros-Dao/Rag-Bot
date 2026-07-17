# ArbiLearn: Web3 Education Platform Features

ArbiLearn is a fully responsive, premium Web3 education platform designed to teach developers the fundamentals of Layer 2 scaling, blockchain principles, and core Web3 concepts through interactive experiences. It is a submission for the Arbitrum Builder Labs — LamprosDAO cohort.

Recently, the ArbiLearn website was modernized with a new tech stack and additional features. Here is what the platform currently includes:

## Modern Tech Stack
- **React 18**: Uses modern component-based architecture instead of raw HTML.
- **Vite**: Provides an ultra-fast build tool and development server.
- **React Router**: Enables seamless single-page navigation between modules without page reloads.
- **CSS3 (Vanilla)**: Utilizes a custom Glassmorphism CSS engine (no Tailwind or Bootstrap required).
- **Web Crypto API**: Native browser API for fast SHA-256 hashing.

## Key Features & Pages

### 1. Home (Landing Page)
Explains why Ethereum needs Layer 2 scaling solutions, specifically Optimistic Rollups like Arbitrum. Features an interactive animated SVG diagram showing the relationship between Ethereum (L1 Base) and Arbitrum (L2 Scale) and how transactions are confirmed.

### 2. Web3 Concepts
Provides side-by-side technical breakdowns and FAQs.
- **Web2 vs Web3**: Explains the transition from centralized internet architecture to decentralized networks.
- **Ethereum vs Bitcoin**: Compares the two leading blockchains.

### 3. Live Prices & Portfolio
Real-time financial dashboard fetching asset prices directly via the **CoinGecko API**. Features include:
- Market filtering options.
- A functional portfolio tracking system to simulate holding Web3 assets.
- Loading states (skeleton loading logic) during data fetching.

### 4. Block Mining Simulator
An interactive educational environment for understanding blockchain immutability.
- Tests **SHA-256 hashes** and **Nonces** live in the browser using the `SubtleCrypto` API.
- Users can simulate mining a block.
- Features a "Chain Broken!" immutability cascade, visually demonstrating what happens if historical blockchain data is altered.
