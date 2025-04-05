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