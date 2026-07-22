package codeforces

import (
	"bufio"
	"io"
	"strconv"
)

var bufSize int = 1000000
var maxTokenSize int = 100000

type Reader struct {
	scanner *bufio.Scanner
}

// Constructor
func NewReader(reader io.Reader) *Reader {
	scanner := bufio.NewScanner(reader)
	scanner.Split(bufio.ScanWords)                      // Now each scan yields one whitespace-delimited token
	scanner.Buffer(make([]byte, bufSize), maxTokenSize) // Total space, and how big each token is allowed to be when scanning
	return &Reader{
		scanner: scanner,
	}
}

// Read in the next integer
func (r *Reader) Int() int {
	r.scanner.Scan()
	nextToken := r.scanner.Text()
	res, _ := strconv.Atoi(nextToken)
	return res
}

// Read in an array of integers
func (r *Reader) Ints(k int) []int {
	slice := make([]int, k)
	for i := range k {
		slice[i] = r.Int()
	}
	return slice
}
