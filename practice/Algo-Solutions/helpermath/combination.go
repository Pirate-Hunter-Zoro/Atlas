package helpermath

type ChooseCalculator struct {
	sols          map[int]map[int]int
	solsMod       map[int]map[int]int
	factorialsMod map[int]int
}

func NewChooseCalculator() *ChooseCalculator {
	calculator := &ChooseCalculator{
		sols:          make(map[int]map[int]int),
		solsMod:       make(map[int]map[int]int),
		factorialsMod: make(map[int]int),
	}
	return calculator
}

func (calculator *ChooseCalculator) Choose(n int, k int) int {
	if k > n {
		return 0
	} else if k == n {
		return 1
	} else if k == 0 {
		return 1
	} else {
		_, ok := calculator.sols[n]
		if !ok {
			calculator.sols[n] = make(map[int]int)
		}
		_, ok = calculator.sols[n][k]
		if !ok {
			calculator.sols[n][k] = calculator.Choose(n-1, k) + calculator.Choose(n-1, k-1)
		}
		return calculator.sols[n][k]
	}
}

func (calculator *ChooseCalculator) factorialMod(n int) int {
	if n == 0 || n == 1 {
		return 1
	}
	_, ok := calculator.factorialsMod[n]
	if !ok {
		calculator.factorialsMod[n] = ModMul(calculator.factorialMod(n-1), n)
	}
	return calculator.factorialsMod[n]
}

func (calculator *ChooseCalculator) ChooseMod(n int, k int) int {
	if k > n {
		return 0
	} else if k == n {
		return 1
	} else if k == 0 {
		return 1
	} else {
		// n! / (k! * (n-k)!) - we can do the division by Fermat's little theorem
		_, ok := calculator.solsMod[n]
		if !ok {
			calculator.solsMod[n] = make(map[int]int)
		}
		_, ok = calculator.solsMod[n][k]
		if ok {
			return calculator.solsMod[n][k]
		}
		numerator := calculator.factorialMod(n)
		denominator := ModMul(calculator.factorialMod(k), calculator.factorialMod(n-k))
		inverseDenominator := ModPow(denominator, MOD-2) // Fermat's little theorem for modular inverse
		result := ModMul(numerator, inverseDenominator)
		calculator.solsMod[n] = make(map[int]int)
		calculator.solsMod[n][k] = result
		return calculator.solsMod[n][k]
	}
}
