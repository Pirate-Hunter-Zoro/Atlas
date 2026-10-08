package finditinerary

import "algo-solutions/datastructures"

/*
You are given a list of airline tickets where tickets[i] = [fromᵢ, toᵢ] represent the departure and the arrival airports of one flight.
Reconstruct the itinerary in order and return it.

All of the tickets belong to a man who departs from "JFK", thus, the itinerary must begin with "JFK".
If there are multiple valid itineraries, you should return the itinerary that has the smallest lexical order when read as a single string.

For example, the itinerary ["JFK", "LGA"] has a smaller lexical order than ["JFK", "LGB"].
You may assume all tickets form at least one valid itinerary.
You must use all the tickets once and only once.

Link:
https://leetcode.com/problems/reconstruct-itinerary/description/?envType=problem-list-v2&envId=graph

Inspiration:
ChatGPT for the alphabetized heaps...
*/
func findItinerary(tickets [][]string) []string {
	// We're have a list of tickets, which means we can create a graph
	graph := make(map[string]*datastructures.Heap[string])
	// Have an outgoing edge to each destination - and sort the destinations in a heap lexicographically
	for _, ticket := range tickets {
		_, ok := graph[ticket[0]]
		if !ok {
			graph[ticket[0]] = datastructures.NewHeap(func(s1, s2 string) bool {
				return s1 < s2
			})
		}
		graph[ticket[0]].Push(ticket[1])
	}
	itinerary := []string{}
	// We need to start at JFK
	exploreStack := datastructures.NewStack[string]()
	exploreStack.Push("JFK")
	for !exploreStack.Empty() {
		// Pop the top node and move it to the queue
		node := exploreStack.Peek()
		if _, ok := graph[node]; ok {
			if !graph[node].Empty() {
				// Pop the top node from this node's heap connections and push it to the stack of nodes - ONLY the top node because now we need to follow this top node
				nextNode := graph[node].Pop()
				exploreStack.Push(nextNode)
			} else {
				// This node has no more connections, so we need to pop it from the stack and add it to the itinerary
				itinerary = append(itinerary, exploreStack.Pop())
			}
		} else {
			// This node had no connections to start with, so we need to pop it from the stack and add it to the itinerary
			// NOTE THAT IF THIS HAPPENS, then the top of the stack is the FIRST element we are appending to the itinerary (and hence in the end the last destination)
			if len(itinerary) > 0 {
				panic("Assertion failed: Itinerary is not empty when the top of the stack has no neighbors - all preceding destinations in the itinerary are chronologically later and cannot be reached.")
			}
			itinerary = append(itinerary, exploreStack.Pop())
		}
	}
	// Reverse the itinerary order now
	for i, j := 0, len(itinerary)-1; i < j; i, j = i+1, j-1 {
		itinerary[i], itinerary[j] = itinerary[j], itinerary[i]
	}

	return itinerary
}
