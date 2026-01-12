package leetcode

import (
	"leet-code/datastructures"
	"reflect"
	"testing"
)

func runTestHelper[I any, A any](t *testing.T, f func(i I) A, inputs []I, expected_outputs []A) {
	for idx, input := range inputs {
		output := f(input)
		expected_output := expected_outputs[idx]
		if !reflect.DeepEqual(output, expected_output) {
			t.Fatalf("Error - expected %v but got %v", expected_output, output)
		}
	}
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestSuperEggDrop(t *testing.T) {
	type input struct {
		n int
		k int
	}

	inputs := []input{
		{n:1, k:2},
		{n:2, k:6},
		{n:3, k:14},
		{n:1, k:1},
		{n:7, k:5000},
	}

	expected_outputs := []int{
		2,3,4,1,13,
	}

	f := func(i input) int {
		return superEggDrop(i.n, i.k)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestLargestRectangleArea(t *testing.T) {
	type input struct {
		heights []int
	}
	inputs := []input{
		{heights : []int{2,1,5,6,2,3}},
		{heights : []int{2,4}},
	}
	
	expected_outputs := []int{
		10,
		4,
	}

	f := func(i input) int {
		return largestRectangleArea(i.heights)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestMaximalRectangle(t *testing.T) {
	type input struct {
		matrix [][]byte
	}
	inputs := []input{
		{matrix: [][]byte{{'1','0','1','0','0'},{'1','0','1','1','1'},{'1','1','1','1','1'},{'1','0','0','1','0'}}},
		{matrix: [][]byte{{'0'}}},
		{matrix: [][]byte{{'1'}}},
	}

	expected_outputs := []int{
		6,0,1,
	}

	f := func(i input) int {
		return maximalRectangle(i.matrix)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestCanFinish(t *testing.T) {
	type input struct {
		numCourses int
		prerequisites [][]int
	}
	inputs := []input{
		{2, [][]int{{1,0}}},
		{2, [][]int{{1,0},{0,1}}},
	}

	expected_outputs := []bool{true, false}

	f := func(i input) bool {
		return canFinish(i.numCourses, i.prerequisites)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestIsMatch(t *testing.T) {
	type input struct {
		s string
		p string
	}
	inputs := []input{
		{"aa", "a"},
		{"aa", "*"},
		{"cb", "?a"},
		{"adceb", "*a*b"},
	}

	expected_outputs := []bool{
		false,
		true,
		false,
		true,
	}

	f := func(i input) bool {
		return isMatch(i.s, i.p)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestFindSubstring(t *testing.T) {
	type input struct {
		s string
		words []string
	}
	inputs := []input{
		{"barfoothefoobarman", []string{"foo","bar"}},
		{"wordgoodgoodgoodbestword", []string{"word","good","best","word"}},
		{"barfoofoobarthefoobarman", []string{"bar","foo","the"}},
		{"aaaaaaaaaaaaaa", []string{"aa","aa"}},
	}

	expected_outputs := [][]int{
		{0,9},
		{},
		{6,9,12},
		{0,1,2,3,4,5,6,7,8,9,10},
	}

	f := func(i input) []int{
		return findSubstring(i.s, i.words)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestFirstMissingPositive(t *testing.T) {
	type input struct {
		nums []int
	}
	inputs := []input{
		{[]int{1,2,0}},
		{[]int{3,4,-1,1}},
		{[]int{7,8,9,11,12}},
	}

	expected_outputs := []int{
		3,
		2,
		1,
	}

	f := func(i input) int {
		return firstMissingPositive(i.nums)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestMergeKLists(t *testing.T) {
	type input struct {
		lists []*datastructures.ListNode
	}
	inputs := []input{
		{
			[]*datastructures.ListNode{
				datastructures.NewListNode([]int{1,4,5}),
				datastructures.NewListNode([]int{1,3,4}),
				datastructures.NewListNode([]int{2,6}),
			},
		},
		{
			[]*datastructures.ListNode{},
		},
		{
			[]*datastructures.ListNode{
				datastructures.NewListNode([]int{}),
			},
		},
	}

	expected_outputs := []*datastructures.ListNode{
		datastructures.NewListNode([]int{1,1,2,3,4,4,5,6}),
		nil,
		nil,
	}

	f := func(i input) *datastructures.ListNode {
		return mergeKLists(i.lists)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestLongestValidParentheses(t *testing.T) {
	type input struct {
		s string
	}
	inputs := []input{
		{"(()"},
		{")()())"},
		{""},
		{"()(())"},
		{")(())(()()))("},
	}

	expected_outputs := []int{
		2,
		4,
		0,
		6,
		10,
	}

	f := func(i input) int {
		return longestValidParentheses(i.s)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestIsScramble(t *testing.T) {
	type input struct {
		s1 string
		s2 string
	}
	inputs := []input{
		{"great","rgeat"},
		{"abcde", "caebd"},
		{"a", "a"},
	}

	expected_outputs := []bool{
		true,
		false,
		true,
	}

	f := func(i input) bool {
		return isScramble(i.s1, i.s2)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestNumDistinct(t *testing.T) {
	type input struct {
		s string
		t string
	}
	inputs := []input{
		{"rabbbit", "rabbit"},
		{"babgbag", "bag"},
		{"b", "a"},
	}

	expected_outputs := []int{
		3,
		5,
		0,
	}

	f := func(i input) int {
		return numDistinct(i.s, i.t)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestMaxStudents(t *testing.T) {
	type input struct {
		seats [][]byte
	}

	inputs := []input{
		{[][]byte{
			{'#','.','#','#','.','#'},
            {'.','#','#','#','#','.'},
            {'#','.','#','#','.','#'},
		}},
		{[][]byte{
			{'.','#'},
            {'#','#'},
            {'#','.'},
			{'#','#'},
			{'.','#'},
		}},
		{[][]byte{
			{'#','.','.','.','#'},
			{'.','#','.','#','.'},
			{'.','.','#','.','.'},
			{'.','#','.','#','.'},
			{'#','.','.','.','#'},
		}},
	}

	expected_outputs := []int{
		4,
		3,
		10,
	}

	f := func(i input) int {
		return maxStudents(i.seats)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestConnectTwoGroups(t *testing.T) {
	type input struct {
		cost [][]int
	}

	inputs := []input{
		{[][]int{{15, 96}, {36, 2}}},
		{[][]int{{1, 3, 5}, {4, 1, 1}, {1, 5, 3}}},
		{[][]int{{2, 5, 1}, {3, 4, 7}, {8, 1, 2}, {6, 2, 4}, {3, 8, 8}}},
	}

	expected_outputs := []int{
		17,
		4,
		10,
	}

	f := func(i input) int {
		return connectTwoGroups(i.cost)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestCandy(t *testing.T) {
	type input struct {
		ratings []int
	}

	inputs := []input{
		{[]int{1,0,2}},
		{[]int{1,2,2}},
	}

	expected_outputs := []int{
		5,
		4,
	}

	f := func(i input) int {
		return candy(i.ratings)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestGetPermutation(t *testing.T) {
	type input struct {
		n int
		k int
	}
	inputs := []input{
		{3,3},
		{4,9},
		{3,1},
		{2,2},
	}

	expected_outputs := []string{
		"213",
		"2314",
		"123",
		"21",
	}

	f := func(i input) string {
		return getPermutation(i.n, i.k)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestFindWords(t *testing.T) {
	type input struct{
		board [][]byte
		words []string
	}
	inputs := []input{
		{[][]byte{
			{'o','a','a','n'},
			{'e','t','a','e'},
			{'i','h','k','r'},
			{'i','f','l','v'},
		}, []string{"oat","oath","pea","eat","rain"}},
		{[][]byte{
			{'a','b'},
			{'c','d'},
		}, []string{"abcb"}},
	}

	expected_outputs := [][]string{
		{"eat","oat","oath"},
		{},
	}

	f := func(i input) []string {
		return findWords(i.board, i.words)
	}

	runTestHelper(t, f, inputs, expected_outputs)

}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestContainsNearbyAlmostDuplicate(t *testing.T) {
	type input struct {
		nums []int
		indexDiff int
		valueDiff int
	}
	inputs := []input{
		{[]int{1,2,3,1}, 3, 0},
		{[]int{1,2,1,1}, 1, 0},
		{[]int{1,5,9,1,5,9}, 2, 3},
		{[]int{-2,3}, 2, 5},
		{[]int{-3,3}, 2, 4},
		{[]int{7,2,8}, 2, 1},
	}

	expected_outputs := []bool{
		true,
		true,
		false,
		true,
		false,
		true,
	}

	f := func(i input) bool {
		return containsNearbyAlmostDuplicate(i.nums, i.indexDiff, i.valueDiff)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestWordBreak(t *testing.T) {
	type input struct {
		s string
		wordDict []string
	}
	inputs := []input{
		{"catsanddog", []string{"cat","cats","and","sand","dog"}},
		{"pineapplepenapple", []string{"apple","pen","applepen","pine","pineapple"}},
		{"catsandog", []string{"cats","dog","sand","and","cat"}},
	}

	expected_outputs := [][]string{
		{"cat sand dog","cats and dog"},
		{"pine apple pen apple", "pine applepen apple", "pineapple pen apple"},
		{},
	}

	f := func(i input) []string {
		return wordBreak(i.s, i.wordDict)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestRemoveBoxes(t *testing.T) {
	type input struct {
		boxes []int
	}
	inputs := []input{
		{[]int{1,3,2,2,2,3,4,3,1}},
		{[]int{1,1,1}},
		{[]int{1}},
		{[]int{1,2,2,1,1,1,2,1,1,2,1,2,1,1,2,2,1,1,2,2,1,1,1,2,2,2,2,1,2,1,1,2,2,1,2,1,2,2,2,2,2,1,2,1,2,2,1,1,1,2,2,1,2,1,2,2,1,2,1,1,1,2,2,2,2,2,1,2,2,2,2,2,1,1,1,1,1,2,2,2,2,2,1,1,1,1,2,2,1,1,1,1,1,1,1,2,1,2,2,1}},
	}

	expected_outputs := []int{
		23,
		9,
		1,
		2758,
	}

	f := func(i input) int {
		return removeBoxes(i.boxes)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestCheckRecord(t *testing.T) {
	type input struct {
		n int
	}
	inputs := []input{
		{2},
		{1},
		{3},
		{10101},
	}

	expected_outputs := []int{
		8,
		3,
		19,
		183236316,
	}

	f := func(i input) int {
		return checkRecord(i.n)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestCanPartition(t *testing.T) {
	type input struct {
		nums []int
	}
	inputs := []input{
		{[]int{1,5,11,5}},
		{[]int{1,2,3,5}},
	}

	expected_outputs := []bool{
		true,
		false,
	}

	f := func(i input) bool {
		return canPartition(i.nums)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestBeautifulNumbers(t *testing.T) {
	type input struct {
		l int
		r int
	}
	inputs := []input{
		{10, 20},
		{1, 15},
		{20, 26},
		{20, 100},
	}

	expected_outputs := []int{
		2,
		10,
		2,
		15,
	}

	f := func(i input) int {
		return beautifulNumbers(i.l, i.r)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestStoneGameV(t *testing.T) {
	type input struct {
		stoneValue []int
	}
	inputs := []input{
		{[]int{6,2,3,4,5,5}},
		{[]int{7,7,7,7,7,7,7}},
		{[]int{4}},
	}
	expected_outputs := []int{
		18,
		28,
		0,
	}

	f := func(i input) int {
		return stoneGameV(i.stoneValue)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestFindMaxForm(t *testing.T) {
	type input struct {
		strs []string
		m int
		n int
	}
	inputs := []input{
		{[]string{"10","0001","111001","1","0"}, 5, 3},
		{[]string{"10","0","1"}, 1, 1},
	}

	expected_outputs := []int{
		4,
		2,
	}

	f := func(i input) int {
		return findMaxForm(i.strs, i.m, i.n)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestIdealArrays(t *testing.T) {
	type input struct {
		n int
		maxValue int
	}
	inputs := []input{
		{2,5},
		{5,3},
		{5878,2900},
	}

	expected_outputs := []int{
		10,
		11,
		465040898,
	}

	f := func(i input) int {
		return idealArrays(i.n, i.maxValue)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestGetMaxRepetitions(t *testing.T) {
	type input struct {
		s1 string
		n1 int
		s2 string
		n2 int
	}
	inputs := []input{
		{"acb", 4, "ab", 2},
		{"acb", 1, "acb", 1},
	}
	expected_outputs := []int{
		2,
		1,
	}

	f := func(i input) int {
		return getMaxRepetitions(i.s1, i.n1, i.s2, i.n2)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestFindItinerary(t *testing.T) {
	type input struct {
		tickets [][]string
	}
	inputs := []input{
		{[][]string{{"MUC","LHR"},{"JFK","MUC"},{"SFO","SJC"},{"LHR","SFO"}}},
		{[][]string{{"JFK","SFO"},{"JFK","ATL"},{"SFO","ATL"},{"ATL","JFK"},{"ATL","SFO"}}},
	}
	expected_outputs := [][]string{
		{"JFK","MUC","LHR","SFO","SJC"},
		{"JFK","ATL","JFK","SFO","ATL","SFO"},
	}

	f := func(i input) []string {
		return findItinerary(i.tickets)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestMaxCoins(t *testing.T) {
	type input struct {
		nums []int
	}
	inputs := []input{
		{[]int{3,1,5,8}},
		{[]int{1,5}},
	}
	expected_outputs := []int{
		167,
		10,
	}

	f := func(i input) int {
		return maxCoins(i.nums)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestFindMinStep(t *testing.T) {
	type input struct {
		board string
		hand string
	}
	inputs := []input{
		{"WRRBBW", "RB"},
		{"WWRRBBWW", "WRBRW"},
		{"G", "GGGGG"},
		{"RBYYBBRRB", "YRBGB"},
	}

	expected_outputs := []int{
		-1,
		2,
		2,
		3,
	}

	f := func(i input) int {
		return findMinStep(i.board, i.hand)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestNumTilings(t *testing.T) {
	type input struct {
		n int
	}
	inputs := []input{
		{3},
		{1},
	}

	expected_outputs := []int{
		5,
		1,
	}

	f := func(i input) int {
		return numTilings(i.n)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestSplitArray(t *testing.T) {
	type input struct {
		nums []int
		k int
	}
	inputs := []input{
		{[]int{7,2,5,10,8}, 2},
		{[]int{1,2,3,4,5}, 2},
		{[]int{1,4,4}, 3},
	}

	expected_outputs := []int{
		18,
		9,
		4,
	}

	f := func(i input) int {
		return splitArray(i.nums, i.k)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestDistributeCookies(t *testing.T) {
	type input struct {
		cookies []int
		k int
	}
	inputs := []input{
		{[]int{8,15,10,20,8}, 2},
		{[]int{6,1,3,2,2,4,1,2}, 3},
	}
	expected_outputs := []int{
		31,
		7,
	}

	f := func(i input) int {
		return distributeCookies(i.cookies, i.k)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestMinTimeToReach(t *testing.T) {
	type input struct {
		moveTime [][]int
	}
	inputs := []input{
		{[][]int{{0,4},{4,4}}},
		{[][]int{{0,0,0},{0,0,0}}},
	}
	expected_outputs := []int{
		6,
		3,
	}

	f := func(i input) int {
		return minTimeToReach(i.moveTime)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestMinTimeToReachII(t *testing.T) {
	type input struct {
		moveTime [][]int
	}
	inputs := []input{
		{[][]int{{0,4},{4,4}}},
		{[][]int{{0,0,0,0},{0,0,0,0}}},
	}

	expected_outputs := []int{
		7,
		6,
	}

	f := func(i input) int {
		return minTimeToReachII(i.moveTime)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestSolveSudoku(t *testing.T) {
	type input struct {
		board [][]byte
	}
	inputs := []input{
		{[][]byte{{'5','3','.','.','7','.','.','.','.'},{'6','.','.','1','9','5','.','.','.'},{'.','9','8','.','.','.','.','6','.'},{'8','.','.','.','6','.','.','.','3'},{'4','.','.','8','.','3','.','.','1'},{'7','.','.','.','2','.','.','.','6'},{'.','6','.','.','.','.','2','8','.'},{'.','.','.','4','1','9','.','.','5'},{'.','.','.','.','8','.','.','7','9'}}},
	}

	expected_outputs := [][][]byte{
		{{'5','3','4','6','7','8','9','1','2'},{'6','7','2','1','9','5','3','4','8'},{'1','9','8','3','4','2','5','6','7'},{'8','5','9','7','6','1','4','2','3'},{'4','2','6','8','5','3','7','9','1'},{'7','1','3','9','2','4','8','5','6'},{'9','6','1','5','3','7','2','8','4'},{'2','8','7','4','1','9','6','3','5'},{'3','4','5','2','8','6','1','7','9'}},
	}

	f := func(i input) [][]byte {
		solveSudoku(i.board)
		return i.board
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestLadderLength(t *testing.T) {
	type input struct {
		beginWord string
		endWord string
		wordList []string
	}
	inputs := []input{
		{"hit", "cog", []string{"hot","dot","dog","lot","log","cog"}},
		{"hit", "cog", []string{"hot","dot","dog","lot","log"}},
	}

	expected_outputs := []int{
		5,
		0,
	}

	f := func(i input) int {
		return ladderLength(i.beginWord, i.endWord, i.wordList)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestNumberOfArithmeticSlices(t *testing.T) {
	type input struct {
		nums []int
	}
	inputs := []input{
		{[]int{2,4,6,8,10}},
		{[]int{7,7,7,7,7}},
	}

	expected_outputs := []int{
		7,
		16,
	}

	f := func(i input) int {
		return numberOfArithmeticSlices(i.nums)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestCountPalindromes(t *testing.T) {
	type input struct {
		s string
	}
	inputs := []input{
		{"103301"},
		{"0000000"},
		{"9999900000"},
	}
	expected_outputs := []int{
		2,
		21,
		2,
	}

	f := func(i input) int {
		return countPalindromes(i.s)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestCatMouseGame(t *testing.T) {
	type input struct {
		graph [][]int
	}
	inputs := []input{
		{[][]int{{2,5},{3},{0,4,5},{1,4,5},{2,3},{0,2,3}}},
		{[][]int{{1,3},{0},{3},{0,2}}},
		{[][]int{{2,3},{2},{0,1},{0,4},{3}}},
	}
	expected_outputs := []int{
		0,
		1,
		2,
	}
	f := func(i input) int {
		return catMouseGame(i.graph)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestFindSecretWord(t *testing.T) {
	firstMaster := NewMaster("acckzz", 10, []string{"acckzz","ccbazz","eiowzz","abcczz"})
	findSecretWord([]string{"acckzz","ccbazz","eiowzz","abcczz"}, firstMaster)
	if firstMaster.GetString() != "You guessed the secret word correctly."  {
		t.Fatalf("Error - expected 'You guessed the secret word correctly.' but got '%s'", firstMaster.GetString())
	}

	secondMaster := NewMaster("hamada", 10, []string{"hamada","khaled"})
	findSecretWord([]string{"hamada","khaled"}, secondMaster)
	if secondMaster.GetString() != "You guessed the secret word correctly." {
		t.Fatalf("Error - expected 'You guessed the secret word correctly.' but got '%s'", secondMaster.GetString())
	}
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestCountGoodArrays(t *testing.T) {
	type input struct {
		n int
		m int
		k int
	}
	inputs := []input{
		{3, 2, 1},
		{4, 2, 2},
		{5, 2, 0},
	}
	expected_outputs := []int{
		4,
		6,
		2,
	}
	f := func(i input) int {
		return countGoodArrays(i.n, i.m, i.k)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestMinimumDeletions(t *testing.T) {
	type input struct {
		word string
		k int
	}
	inputs := []input{
		{"aabcaba", 0},
		{"dabdcbdcdcd", 2},
		{"aaabaaa", 2},
	}

	expected_outputs := []int{
		3,
		2,
		1,
	}

	f := func(i input) int {
		return minimumDeletions(i.word, i.k)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestMinDeletions(t *testing.T) {
	type input struct {
		s string
	}
	inputs := []input{
		{"aab"},
		{"aaabbbcc"},
		{"ceabaacb"},
	}

	expected_outputs := []int{
		0,
		2,
		2,
	}

	f := func(i input) int {
		return minDeletions(i.s)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestMatchPlayersAndTrainers(t *testing.T) {
	type input struct {
		players []int
		trainers []int
	}
	inputs := []input{
		{[]int{4,7,9}, []int{8,2,5,8}},
		{[]int{1,1,1}, []int{10}},
	}

	expected_outputs := []int{
		2,
		1,
	}

	f := func(i input) int {
		return matchPlayersAndTrainers(i.players, i.trainers)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestPathSum(t *testing.T) {
	type input struct {
		root *datastructures.TreeNode
		targetSum int
	}
	inputs := []input{
		{datastructures.NewTreeNode([]int{5,4,8,11,-1,13,4,7,2,-1,-1,5,1}), 22},
		{datastructures.NewTreeNode([]int{1,2,3}), 5},
		{datastructures.NewTreeNode([]int{1,2}), 0},
	}

	expected_outputs := [][][]int{
		{{5,4,11,2},{5,8,4,5}},
		{},
		{},
	}

	f := func(i input) [][]int {
		return pathSum(i.root, i.targetSum)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestMaximumLength(t *testing.T) {
	type input struct {
		nums []int
	}
	inputs := []input{
		{[]int{1,2,3,4}},
		{[]int{1,2,1,1,2,1,2}},
		{[]int{1,3}},
	}
	expected_outputs := []int{
		4,
		6,
		2,
	}

	f := func(i input) int {
		return maximumLength(i.nums)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

/////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestMaximumLengthII(t *testing.T) {
	type input struct {
		nums []int
		k    int
	}
	inputs := []input{
		{[]int{1,2,3,4,5}, 2},
		{[]int{1,4,2,3,1,4}, 3},
	}

	expected_outputs := []int{
		5,
		4,
	}

	f := func(i input) int {
		return maximumLengthII(i.nums, i.k)
	}
	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestMinimumDifference(t *testing.T) {
	type input struct {
		nums []int
	}
	inputs := []input{
		{[]int{3,1,2}},
		{[]int{7,9,5,8,1,3}},
	}

	expected_outputs := []int64{
		-1,
		1,
	}

	f := func(i input) int64 {
		return minimumDifference(i.nums)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestWaysToBuildRooms(t *testing.T) {
	type input struct {
		prevRoom []int
	}
	inputs := []input{
		{[]int{-1,0,1}},
		{[]int{-1,0,0,1,2}},
	}

	expected_outputs := []int{
		1,
		6,
	}

	f := func(i input) int {
		return waysToBuildRooms(i.prevRoom)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestLengthOfLIS(t *testing.T) {
	type input struct {
		nums []int
	}
	inputs := []input{
		{[]int{10,9,2,5,3,7,101,18}},
		{[]int{0,1,0,3,2,3}},
		{[]int{7,7,7,7,7,7,7}},
	}
	expected_outputs := []int{
		4,
		4,
		1,
	}

	f := func(i input) int {
		return lengthOfLIS(i.nums)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

func TestLengthOfLISFast(t *testing.T) {
	type input struct {
		nums []int
	}
	inputs := []input{
		{[]int{10,9,2,5,3,7,101,18}},
		{[]int{0,1,0,3,2,3}},
		{[]int{7,7,7,7,7,7,7}},
	}
	expected_outputs := []int{
		4,
		4,
		1,
	}

	f := func(i input) int {
		return lengthOfLISFast(i.nums)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestCoinChange(t *testing.T) {
	type input struct {
		coins []int
		amount int
	}
	inputs := []input{
		{[]int{1,2,5}, 11},
		{[]int{2}, 3},
		{[]int{1}, 0},
	}
	expected_output := []int{
		3,
		-1,
		0,
	}

	f := func(i input) int {
		return coinChange(i.coins, i.amount)
	}

	runTestHelper(t, f, inputs, expected_output)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestMinCost(t *testing.T) {
	type input struct {
		maxTime int
		edges [][]int 
		passingFees []int
	}
	inputs := []input{
		{30, [][]int{{0,1,10},{1,2,10},{2,5,10},{0,3,1},{3,4,10},{4,5,15}}, []int{5,1,2,20,20,3}},
		{29, [][]int{{0,1,10},{1,2,10},{2,5,10},{0,3,1},{3,4,10},{4,5,15}}, []int{5,1,2,20,20,3}},
		{25, [][]int{{0,1,10},{1,2,10},{2,5,10},{0,3,1},{3,4,10},{4,5,15}}, []int{5,1,2,20,20,3}},
		{10, [][]int{{0,1,2},{0,2,1},{0,3,10},{1,3,2},{3,2,2},{4,3,1}}, []int{1,1,3,2,1}},
	}
	expected_outputs := []int{
		11,
		48,
		-1,
		5,
	}

	f := func(i input) int {
		return minCost(i.maxTime, i.edges, i.passingFees)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestFindRedundantConnection(t *testing.T) {
	type input struct {
		edges [][]int
	}
	inputs := []input{
		{[][]int{{1,2},{1,3},{2,3}}},
		{[][]int{{1,2},{2,3},{3,4},{1,4},{1,5}}},
	}
	expected_outputs := [][]int{
		{2,3},
		{1,4},
	}

	f := func(i input) []int {
		return findRedundantConnection(i.edges)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestFindRedundantDirectedConnection(t *testing.T) {
	type input struct {
		edges [][]int
	}
	inputs := []input{
		{[][]int{{1,2},{1,3},{2,3}}},
		{[][]int{{1,2},{2,3},{3,4},{4,1},{1,5}}},
	}
	expected_outputs := [][]int{
		{2,3},
		{4,1},
	}

	f := func(i input) []int {
		return findRedundantDirectedConnection(i.edges)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestMinDistance(t *testing.T) {
	type input struct {
		word1 string
		word2 string
	}
	inputs := []input{
		{"horse", "ros"},
		{"intention", "execution"},
	}
	expected_outputs := []int{
		3,
		5,
	}

	f := func(i input) int {
		return minDistance(i.word1, i.word2)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestMaxProfit(t *testing.T) {
	type input struct {
		n int
		present []int
		future []int
		hierarchy [][]int
		budget int
	}
	inputs := []input{
		{2, []int{1,2}, []int{4,3}, [][]int{{1,2}}, 3},
		{2, []int{3,4}, []int{5,8}, [][]int{{1,2}}, 4},
		{3, []int{4,6,8}, []int{7,9,11}, [][]int{{1,2},{1,3}}, 10},
		{3, []int{5,2,3}, []int{8,5,6}, [][]int{{1,2},{2,3}}, 7},
	}

	expected_outputs := []int{
		5,
		4,
		10,
		12,
	}

	f := func(i input) int {
		return maxProfit(i.n, i.present, i.future, i.hierarchy, i.budget)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestLongestConsecutive(t *testing.T) {
	type input struct {
		nums []int
	}
	inputs := []input{
		{[]int{100,4,200,1,3,2}},
		{[]int{0,3,7,2,5,8,4,6,0,1}},
		{[]int{1,0,1,2}},
		{[]int{1,2,0,1}},
	}

	expected_outputs := []int{
		4,
		9,
		3,
		3,
	}

	f := func(i input) int {
		return longestConsecutive(i.nums)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestMaxMoves(t *testing.T) {
	type input struct {
		kx int
		ky int
		positions [][]int
	}
	inputs := []input{
		{1, 1, [][]int{{0,0}}},
		{0, 2, [][]int{{1,1},{2,2},{3,3}}},
		{0, 0, [][]int{{1,2},{2,4}}},
		{49, 49, [][]int{{0,0}}},
	}

	expected_outputs := []int{
		4,
		8,
		3,
		34,
	}

	f := func(i input) int {
		return maxMoves(i.kx, i.ky, i.positions)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestIsRegexMatch(t *testing.T) {
	type input struct {
		s string
		p string
	}
	inputs := []input {
		{"aa", "a"},
		{"aa", "a*"},
		{"ab", ".*"},
		{"aab", "c*a*b"},
	}

	expected_outputs := []bool{
		false,
		true,
		true,
		true,
	}

	f := func(i input) bool {
		return isRegexMatch(i.s, i.p)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestFindMedianSortedArrays(t *testing.T) {
	type input struct {
		nums1 []int
		nums2 []int
	}
	inputs := []input{
		{[]int{1,3}, []int{2}},
		{[]int{1,2}, []int{3,4}},
	}

	expected_outputs := []float64{
		2.00000,
		2.50000,
	}

	f := func(i input) float64 {
		return findMedianSortedArrays(i.nums1, i.nums2)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}

////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

func TestCanMouseWin(t *testing.T) {
	type input struct {
		grid []string
		catJump int
		mouseJump int
	}
	inputs := []input{
		{[]string{"####F","#C...","M...."}, 1, 2},
		{[]string{"M.C...F"}, 1, 4},
		{[]string{"M.C...F"}, 1, 3},
	}

	expected_outputs := []bool{
		true,
		true,
		false,
	}

	f := func(i input) bool {
		return canMouseWin(i.grid, i.catJump, i.mouseJump)
	}

	runTestHelper(t, f, inputs, expected_outputs)
}