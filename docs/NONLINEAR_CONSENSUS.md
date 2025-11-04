# Non-Linear Consensus: Pythagorean³

## Foreword

This theory emerged from the need of using small models for semantic search in a vector database using cosine similarity. Two models were tested individually: GraphCodeBERT and UniXcoder, their key differences follow:

| Aspect    | GraphCodeBERT                           | UniXCoder                           |
|-----------|-----------------------------------------|-------------------------------------|
| Structure | Data flow graphs                        | AST + comments                      |
| Modes     | Primarily encoder                       | Encoder/Decoder/Both                |
| Languages | 6 languages                             | 9 languages                         |
| Focus     | Semantic relationships via data flow    | Cross-modal flexibility             |
| Use case  | Better for understanding code semantics | More versatile for generation tasks |

Generically speaking, GraphCodeBERT is semantic biased and UniXCoder is structure/code biased - both fundamentally based on RoBERTa (Robustly Optimized BERT):

During tests GraphCodeBERT excelled in natural language searches and UniXCoder excelled in code specific search, creating the following scenario when generating embeddings from small functions (as setters and getters):
- GraphCodeBERT: generalize the embeddings into "one that fits them all" (setter/getter);
- UniXCoder: specify the embeddings with content distinction (setter of x/getter of y), but would fail to translate the natural language query into the code lookup;

The natural approach: combine both.

Pythagorean³ was chosen from gut feeling, knowing it would preserve the sign, amplify the signal, and increase the 'contrast' in the embedding vector, attenuating noise and filtering uncertainties. After some deliberation and lots of analysis, what helped to understand its effect was the XNOR analogy: Pythagorean³ acts as lossy multiplexation with noise filtering. 


## Mathematical Foundation

Traditional embedding fusion uses linear combination (averaging). Non-linear consensus employs element-wise Pythagorean³ operation:

For normalized embedding vectors **a** and **b** (each dimension in [-1, 1]):

```
consensus[i] = cbrt(a[i]³ + b[i]³)
```

Applied element-wise across all dimensions.

## Sign Preservation

Unlike Pythagorean² (sqrt(a² + b²)), which always produces positive output and loses directional information, Pythagorean³ preserves sign:

```
Pythagorean²:  sqrt(0.6² + (-0.6)²) = sqrt(0.72) = 0.85  ✗ (sign lost)
Pythagorean³:  cbrt(0.6³ + (-0.6)³) = cbrt(0) = 0        ✓ (cancellation)
```

**Why sign matters:** Embedding dimensions encode semantic meaning through both magnitude and direction. Positive vs negative values often represent opposing semantic features (e.g., "imperative" vs "functional", "sync" vs "async"). Destroying sign information collapses semantic structure.

## Disagreement Cancellation

When models produce opposite signals, cubing amplifies the conflict:

```
a =  0.7 (Model A: positive signal)
b = -0.7 (Model B: negative signal)

a³ + b³ = 0.343 + (-0.343) = 0
cbrt(0) = 0
```

Complete disagreement produces zero output. This implements **noise filtering**: when complementary models disagree about a feature's presence, the disagreement suggests uncertainty or false positive. The consensus mechanism suppresses this uncertain signal.

**Partial disagreement:**
```
a =  0.6
b = -0.3

a³ + b³ = 0.216 + (-0.027) = 0.189
cbrt(0.189) = 0.574
```

Partial disagreement produces attenuated signal. The stronger signal (0.6) dominates but is tempered by the conflicting weaker signal.

## Consensus Amplification

When models agree in direction, cubing emphasizes the consensus:

```
a = 0.6 (both positive)
b = 0.5

a³ + b³ = 0.216 + 0.125 = 0.341
cbrt(0.341) = 0.699

vs linear average: (0.6 + 0.5) / 2 = 0.550
```

Agreement produces superlinear amplification (0.699 > 0.550). This implements **signal amplification**: when complementary models independently agree about a feature's presence, the agreement suggests genuine semantic match. The consensus mechanism amplifies this confident signal.

## Weak Signal Suppression

For small values (|x| < 1), cubing suppresses more aggressively than squaring:

```
x = 0.3

x²  = 0.09
x³  = 0.027
```

This means weak, uncertain signals from individual models contribute less to the consensus than linear averaging would suggest. Only strong signals (|x| > 0.5) meaningfully contribute.

**Combined with two weak signals:**
```
a = 0.3
b = 0.2

Linear: 0.25
Pythagorean³: cbrt(0.027 + 0.008) = cbrt(0.035) = 0.327
```

Even with agreement, weak signals remain weak. This prevents noise accumulation.

## Behavioral Characterization

Pythagorean³ implements a **continuous, magnitude-weighted consensus function** analogous to XNOR (agreement detector) in digital logic:

**Digital XNOR:**
```
XNOR(1, 1) = 1  (agreement → output)
XNOR(0, 0) = 1  (agreement → output)
XNOR(1, 0) = 0  (disagreement → suppress)
```

**Pythagorean³ analog:**
- Agreement in direction → amplified signal
- Disagreement → canceled/suppressed signal
- Magnitude determines strength of effect (adaptive)
- Preserves continuous semantic structure (not binary)

This makes it suitable for embedding fusion where:
- Direction encodes semantic properties
- Magnitude encodes confidence/strength
- Agreement between independent models suggests validity
- Disagreement suggests uncertainty or false positives

## Non-Linear Consensus as Agreement-Weighted Validation

**Intuitive interpretation:** Pythagorean³ consensus behaves **analogously to differential filtering** by emphasizing agreement and suppressing disagreement between models. This is a useful conceptual model, not a rigorous mathematical equivalence.

**Comparison of fusion approaches:**

**Standard averaging (linear fusion):**
```
result = (a + b) / 2
```
- Preserves **absolute signal magnitude**
- Treats all values equally regardless of inter-model agreement
- Democratic approach: all signals weighted equally

**Pythagorean³ (non-linear consensus):**
```
result = cbrt(a³ + b³)
```
- Emphasizes **relative agreement/disagreement** between models
- Amplifies consensus, suppresses conflict
- Unanimous approach: requires cross-model validation

**Agreement-based filtering (metaphorical, not mathematical):**

Consider the **inter-model agreement** as a measure of signal reliability:

```python
# Agreement score (0 = perfect conflict, 1 = perfect alignment)
agreement = 1 - |a - b| / max_possible_diff

# Pythagorean³ behavior as function of agreement:
if agreement → 1.0:  # Models align
    P³(a,b) > linear_avg(a,b)  # Superlinear amplification

if agreement → 0.0:  # Models conflict
    P³(a,b) < linear_avg(a,b)  # Sublinear suppression

if a ≈ -b:  # Perfect disagreement
    P³(a,b) → 0  # Complete cancellation
```

**Useful conceptual model (not rigorous mathematics):**
- **High agreement** = models converge → **pattern** (genuine signal)
- **High disagreement** = models diverge → **noise** (uncertain signal)

**Information-theoretic formalization:**

**Pattern (validated signal):**
- Both models independently encode similar value
- **Redundant information** → high confidence → genuine semantic feature
- Probability that BOTH models are wrong AND agree: **very low**
- Action: **Amplify** via cubing (superlinear boost)

**Noise (model-specific artifact):**
- Models encode conflicting values
- **Discordant information** → low confidence → likely false positive or model bias
- One or both models confused, overfitting, or hallucinating
- Action: **Suppress** via cancellation (disagreement → 0)

**Cubing as sensitivity parameter:**
```
Low agreement (0.0-0.4):   a³ + b³ → smaller than linear average
Medium agreement (0.4-0.7): a³ + b³ → comparable to linear average
High agreement (0.7-1.0):   a³ + b³ → larger than linear average
Perfect conflict (a = -b):  a³ + b³ = 0 → complete removal
```

**Differential corpus perception:**

**Absolute corpus representation (single model):**
```
Model A sees corpus: [features f₁, f₂, f₃, ...]
→ Embedding: [0.6, -0.3, 0.8, ...]
```

**Differential corpus representation (consensus):**
```
Model A sees: [0.6, -0.3, 0.8]
Model B sees: [0.5, -0.2, 0.1]

Agreement map:    [HIGH, HIGH, LOW]
                   ↓      ↓     ↓
Consensus result: [0.70, -0.32, 0.47]
                  amplify amplify suppress

Interpretation:
- f₁, f₂: Both models agree → validated pattern → reinforce
- f₃: Models disagree (0.8 vs 0.1) → uncertain feature → attenuate
```

**The result is a "consensus-filtered view" of the corpus:**
- Emphasizes features with **inter-model validation**
- Suppresses features with **model-specific bias**
- Effectively computes: "What do both paradigms independently agree exists?"

**Connection to ensemble learning:**

| Method | Decision Rule | Consensus Mechanism |
|--------|--------------|---------------------|
| **Voting** | Majority wins | Democratic (any signal counts equally) |
| **Averaging** | Mean of signals | Democratic (weighted by magnitude) |
| **Pythagorean³** | Agreement amplification | Unanimous (require cross-model validation) |

Standard ensembles use democratic voting or averaging. Pythagorean³ requires **unanimous decision** with magnitude-weighted confidence.

**Multi-order derivative analogy:**

Extending the physics metaphor to multi-model and multi-layer scenarios:

```
Zero-order (position):     Single model, single layer
                          f(x) = layer_embedding

First-order spatial:       Cross-model at fixed layer
                          ∂f/∂(model) = consensus at layer L

First-order temporal:      Single model across layers
                          ∂f/∂L = layer evolution within model

Second-order (mixed):      Cross-model AND cross-layer
                          ∂²f/∂(model)∂L = full spatio-temporal validation

Hybrid fusion:            Phase 1 (spatial) + Phase 2 (temporal)
                          Validates across both model space and processing depth
```

**Formal definition:**

```python
def consensus_derivative(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """
    Compute consensus-filtered representation via differential validation.

    Behaves as differential operator on inter-model agreement:
    - High agreement → amplification (pattern detection)
    - Low agreement → suppression (noise filtering)
    - Perfect conflict → cancellation (false positive removal)

    Information-theoretic interpretation:
        Approximates mutual information I(Model_A ; Model_B | corpus)
        Emphasizes signals present in both model representations
        Suppresses signals unique to single model (artifacts)

    Args:
        a, b: Model embeddings (normalized to [-1, 1])

    Returns:
        Consensus embedding emphasizing validated patterns
    """
    return np.cbrt(a**3 + b**3)
```

**Theoretical significance:**

The "derivative perception" interpretation unifies multiple concepts:

1. **Signal processing**: Differential filters emphasize changes, suppress constants
2. **Information theory**: Mutual information between model representations
3. **Ensemble learning**: Unanimous validation rather than democratic voting
4. **Noise filtering**: Remove "discordant frequencies" (conflicting signals)

Pythagorean³ besides being a fusion method also acts as a **differential cross-model validation mechanism** that computes how much information is consistently present across independent representational paradigms.

---

## Manifold Geometry Interpretation

Recent mechanistic interpretability work on transformer models reveals that learned representations often take the form of **curved manifolds embedded in low-dimensional subspaces**, rather than collections of discrete orthogonal features[^1]. This geometric perspective provides deeper theoretical grounding for Pythagorean³ consensus.

### Embeddings as Manifolds

When models learn to represent structured concepts (ordinal quantities, semantic relationships, hierarchical categories), they don't allocate orthogonal dimensions for each value. Instead, they learn **1-dimensional manifolds with intrinsic curvature** embedded in low-dimensional subspaces. The curvature (rippling pattern) optimally balances:
- **Capacity constraints** (limited dimensionality)
- **Distinguishability** (different values must be separable)

For our two embedding models:
- **GraphCodeBERT:** Manifold encoding semantic relationships (data flow, conceptual structure)
- **UniXcoder:** Manifold encoding syntactic/structural patterns (AST relationships, code form)

Both manifolds represent "the same codebase" but from complementary geometric perspectives.

### P³ as Curvature Alignment

Element-wise Pythagorean³ can be understood as **checking whether two manifolds curve coherently**:

```python
consensus[i] = cbrt(a[i]³ + b[i]³)
```

**At each dimension i:**
- If both manifolds curve the same way → curvature reinforces → amplified signal
- If manifolds curve oppositely → curvatures cancel → suppressed signal
- Cubing emphasizes the curvature (rate of change) rather than just position

**This differs from linear averaging**, which preserves position regardless of curvature agreement.

### Cross-Manifold Validation

The consensus mechanism validates **what geometric structure is consistent across independent representations**:

**Pattern (validated signal):**
- Both models independently encode similar curvature
- The manifolds "ripple" coherently
- High confidence this structure reflects genuine corpus patterns

**Noise (model-specific artifact):**
- Manifolds curve in conflicting directions
- One model's geometric bias, not shared structure
- Suppressed via cancellation

This aligns with findings that transformer attention mechanisms can **rotate manifolds** to check alignment at specific offsets[^1]. P³ performs analogous validation: when manifolds align geometrically after cubing, the consensus is genuine.

### Hierarchical Composition

Just as semantic hierarchies emerge from **cascading manifold transformations** (tokens → words → phrases → concepts through geometric operations), P³ consensus operates at the **embedding manifold level**:

- Input: Two independently learned manifolds
- Operation: Element-wise curvature comparison via cubing
- Output: Consensus manifold emphasizing shared geometric structure

The consensus manifold inherits validated curvature from both inputs while suppressing divergent artifacts.

### Theoretical Implications

**1. P³ is geometrically aligned with transformer representations**
- Not an arbitrary fusion heuristic
- Operates on the natural geometric structure transformers learn
- Validates cross-model patterns at the manifold level

**2. Sign preservation is crucial for curvature**
- Manifold curvature has direction (concave vs convex)
- P³ preserves directional information (unlike P²)
- Enables cancellation when curvatures oppose

**3. Weak signal suppression reflects uncertainty geometry**
- Small embedding values = uncertain/weak manifold curvature
- Cubing suppresses uncertain structure more than averaging would
- Requires strong, confident curvature from both models

**4. Agreement amplification validates geometric consensus**
- When both manifolds confidently encode similar curvature
- Superlinear amplification reflects high-confidence validation
- Emergent from manifold alignment, not explicit design

---

**Formal Perspective:**

If embeddings **a** and **b** represent points on learned manifolds M_A and M_B:

```
P³(a, b) ≈ checking if ∇M_A ≈ ∇M_B
```

Where ∇M represents manifold curvature (local geometric structure). Agreement in curvature → validated pattern. Divergence → artifact suppression.

This provides information-theoretic grounding: P³ approximates **mutual information I(M_A ; M_B | corpus)** by emphasizing geometric structures present in both manifold representations.

---

**Note:** This section extends theoretical understanding but doesn't change practical implementation. The P³ operation remains the same; this provides geometric interpretation of *why* it works.

---

[^1]: Gurnee, W., Ameisen, E., Kauvar, I., et al. (2025). "When Models Manipulate Manifolds: The Geometry of a Counting Task." *Transformer Circuits Thread*. https://transformer-circuits.pub/2025/linebreaks/