package generatetrees

import "algo-solutions/datastructures"

/*
Given an integer n, return all the structurally unique BST's (binary search trees), which has exactly n nodes of unique values from 1 to n. 
Return the answer in any order.

Link:
https://leetcode.com/problems/unique-binary-search-trees-ii/description/
*/
func generateTrees(n int) []*datastructures.TreeNode {
    var solve func(n int, offset int) []*datastructures.TreeNode;
    solve = func(n int, offset int) []*datastructures.TreeNode {
        if n == 1 {
            return []*datastructures.TreeNode{
                {
                    Val: 1+offset,
                    Left: nil,
                    Right: nil,
                },
            }
        } else {
            all_possible := []*datastructures.TreeNode{}
            
            // Lowest is root
            right_possibilities := solve(n-1, offset+1)
            for _, tree := range right_possibilities {
                all_possible = append(all_possible, &datastructures.TreeNode{
                    Val: 1+offset,
                    Left: nil,
                    Right: tree,
                })
            }            

            // Anything in middle is root
            for mid:=2; mid<n; mid++ {
                left_possibilities := solve(mid-1, offset)
                right_possibilities := solve(n-mid, offset+mid)
                for _, left_tree := range left_possibilities {
                    for _, right_tree := range right_possibilities {
                        all_possible = append(all_possible, &datastructures.TreeNode{
                            Val: mid+offset,
                            Left: left_tree,
                            Right: right_tree,
                        })
                    }
                }
            }

            // Highest is root
            left_possibilities := solve(n-1, offset)
            for _, tree := range left_possibilities {
                all_possible = append(all_possible, &datastructures.TreeNode{
                    Val: n+offset,
                    Left: tree,
                    Right: nil,
                })
            }
            
            return all_possible
        }
    }

    return solve(n, 0)
}