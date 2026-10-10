package helpermath

func ModAdd(a, b, mod int) int {
	return ((a % mod) + (b % mod)) % mod
}
func ModSub(a, b, mod int) int {
	return ((a % mod) - (b % mod) + mod) % mod
}
func ModMul(a, b, mod int) int {
	return ((a % mod) * (b % mod)) % mod
}
func ModPow(base, exp, mod int) int {
	result := 1
	base = base % mod
	if base == 0 {
		return 0 // In case base is divisible by mod
	}
	for exp > 0 {
		if (exp & 1) == 1 { // If exp is odd
			result = ModMul(result, base, mod)
		}
		exp >>= 1                      // Divide exp by 2
		base = ModMul(base, base, mod) // Square the base
	}
	return result
}
