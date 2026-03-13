# LeetCode Solutions (Go)

## Overview

This repository contains a structured collection of Go solutions for LeetCode algorithmic problems. It is designed with modularity in mind, separating reusable core data structures and mathematical helper functions from the actual problem-solving logic.

## Project Structure

### Core Solutions

* **`solution.go`**: Contains the primary algorithmic logic for the currently targeted LeetCode problem.
* **`solution_test.go`**: Contains the testing suite to verify the logic in `solution.go` against expected edge cases and standard inputs.

### Data Structures (`/datastructures`)

A library of custom data structures frequently required for optimal algorithmic performance:

* **Disjoint Set (Union-Find)**: `dijsointset.go` (Note: Pending rename to `disjointset.go`)
* **Heap / Priority Queue**: `heap.go`
* **Linked List**: `linkedlist.go`, `listnode.go`
* **Tree**: `treenode.go`
* **Trie (Prefix Tree)**: `trie.go`

### Mathematical Helpers (`/helpermath`)

A collection of mathematical utility functions used to simplify complex numeric problems:

* **Combinatorics**: `combination.go`
* **Modulo Arithmetic**: `modulo.go`
* **Primes (Sieve/Checking)**: `primes.go`

## Getting Started

### Prerequisites

* Go (Version 1.25.0 or higher)

### Running Tests

To execute the test suite for the current solution, navigate to the root directory and run the following command:

```bash
go test -v
