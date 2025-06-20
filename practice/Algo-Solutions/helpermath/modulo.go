package helpermath

var MOD = 1000000007

func ModAdd(a, b int) int {
	return ((a % MOD) + (b % MOD)) % MOD
}
func ModSub(a, b int) int {
	return ((a % MOD) - (b % MOD) + MOD) % MOD
}
func ModMul(a, b int) int {
	return ((a % MOD) * (b % MOD)) % MOD
}
func ModPow(base, exp int) int {
	result := 1
	base = base % MOD
	if base == 0 {
		return 0 // In case base is divisible by MOD
	}
	for exp > 0 {
		if (exp & 1) == 1 { // If exp is odd
			result = ModMul(result, base)
		}
		exp >>= 1 // Divide exp by 2
		base = ModMul(base, base) // Square the base
	}
	return result
}