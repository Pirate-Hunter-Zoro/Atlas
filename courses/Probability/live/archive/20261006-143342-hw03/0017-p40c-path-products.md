---
kind: lesson
title: p40c-path-products
---
**Done. Problem 40(c)(b), the prisoner with no repeated doors, now shows your path products.** The variance part reads:

$$P(X=5) = \tfrac13\cdot\tfrac12\cdot 2 = \tfrac13 \quad (\text{doors } 1,2,3 \text{ or } 2,1,3)$$

$$P(X=2) = \tfrac13\cdot\tfrac12 = \tfrac16 \quad (\text{doors } 1,3), \qquad P(X=3) = \tfrac13\cdot\tfrac12 = \tfrac16 \quad (\text{doors } 2,3)$$

$$P(X=0) = \tfrac13 \quad (\text{door } 3)$$

$$S = \tfrac13\cdot 25 + \tfrac16\cdot 4 + \tfrac16\cdot 9 = \tfrac{21}{2}, \qquad \mathrm{Var}(X) = \tfrac{21}{2} - \tfrac{25}{4} = \tfrac{17}{4}$$

The $\cdot\, 2$ in the first line counts the two orders that both take 5 days. The four probabilities sum to 1, as they must. The PDF is rebuilt: `homework/hw03/build/hw03.pdf`, 4 pages, 0 warnings.
