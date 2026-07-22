package main

import (
	"algo-solutions/codeforces"
	"fmt"
	"os"
)

/*
Mocha wants to be an astrologer. There are 𝑛 stars which can be seen in Zhijiang, and the brightness of the 𝑖-th star is 𝑎𝑖.

Mocha considers that these 𝑛 stars form a constellation, and she uses (𝑎1,𝑎2,…,𝑎𝑛) to show its state.
A state is called mathematical if all of the following three conditions are satisfied:
- For all 𝑖 (1≤𝑖≤𝑛), 𝑎𝑖 is an integer in the range [𝑙𝑖,𝑟𝑖].
- ∑𝑎𝑖 ≤ 𝑚.
- gcd(𝑎1,𝑎2,…,𝑎𝑛)=1.
Here, gcd(𝑎1,𝑎2,…,𝑎𝑛) denotes the greatest common divisor (GCD) of integers 𝑎1,𝑎2,…,𝑎𝑛.

Mocha is wondering how many different mathematical states of this constellation exist. Because the answer may be large, you must find it modulo 998244353.

Two states (𝑎1,𝑎2,…,𝑎𝑛) and (𝑏1,𝑏2,…,𝑏𝑛) are considered different if there exists 𝑖 (1≤𝑖≤𝑛) such that 𝑎𝑖≠𝑏𝑖.

Input:
- The first line contains two integers 𝑛 and 𝑚 (2≤𝑛≤50, 1≤𝑚≤100000) — the number of stars and the upper bound of the sum of the brightness of stars.

Each of the next 𝑛 lines contains two integers 𝑙𝑖 and 𝑟𝑖 (1≤𝑙𝑖≤𝑟𝑖≤𝑚) — the range of the brightness of the 𝑖th star.

Output
Print a single integer — the number of different mathematical states of this constellation, modulo 998244353.

Link:
https://codeforces.com/contest/1559/problem/E
*/
func main() {
	reader := codeforces.NewReader(os.Stdin)
	var n, m int
	n, m = reader.Int(), reader.Int()

	l := make([]int, n)
	r := make([]int, n)

	for i := range n {
		l[i] = reader.Int()
		r[i] = reader.Int()
	}

	fmt.Printf("%d\n", solve(n, m, l, r))
}
