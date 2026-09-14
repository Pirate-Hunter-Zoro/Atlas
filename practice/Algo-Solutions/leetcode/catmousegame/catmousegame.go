package catmousegame

import "algo-solutions/datastructures"

/*
A game on an undirected graph is played by two players, Mouse and Cat, who alternate turns.

The graph is given as follows: graph[a] is a list of all nodes b such that ab is an edge of the graph.

The mouse starts at node 1 and goes first, the cat starts at node 2 and goes second, and there is a hole at node 0.

During each player's turn, they must travel along one edge of the graph that meets where they are.  For example, if the Mouse is at node 1, it must travel to any node in graph[1].

Additionally, it is not allowed for the Cat to travel to the Hole (node 0).

Then, the game can end in three ways:
- If ever the Cat occupies the same node as the Mouse, the Cat wins.
- If ever the Mouse reaches the Hole, the Mouse wins.
- If ever a position is repeated (i.e., the players are in the same position as a previous turn, and it is the same player's turn to move), the game is a draw.
Given a graph, and assuming both players play optimally, return
- 1 if the mouse wins the game,
- 2 if the cat wins the game, or
- 0 if the game is a draw.
*/
func catMouseGame(graph [][]int) int {
	type state struct {
		mouse    int      // mouse position
		cat      int      // cat position
		turn     int      // 0 for mouse, 1 for cat
		children []*state // children states
		parents  []*state // parents states
	}

	// Create a graph all possible states
	states := make([][][]*state, len(graph))
	for i := range states {
		states[i] = make([][]*state, len(graph))
		for j := range states[i] {
			states[i][j] = make([]*state, 2)
		}
	}
	// Also a map for easy iteration of states
	allStates := make(map[*state]bool)
	for mousePosn := range graph {
		for catPosn := range graph {
			if catPosn == 0 {
				// Cat can't go to hole
				continue
			} else {
				for turn := range 2 {
					states[mousePosn][catPosn][turn] = &state{mouse: mousePosn, cat: catPosn, turn: turn, children: make([]*state, 0), parents: make([]*state, 0)}
					// Add this state to the map of all states
					allStates[states[mousePosn][catPosn][turn]] = true
				}
			}
		}
	}

	// Establish the children states for each state
	for mousePosn := range graph {
		for catPosn := range graph {
			if catPosn != 0 && mousePosn != catPosn && mousePosn != 0 {
				// Both possible and non-terminal state
				for turn := range 2 {
					currentState := states[mousePosn][catPosn][turn]
					if turn == 0 {
						// Mouse's turn - can move to any of the neighbors
						for _, neighbor := range graph[mousePosn] {
							childState := states[neighbor][catPosn][1] // Cat's turn next
							currentState.children = append(currentState.children, childState)
							childState.parents = append(childState.parents, currentState)
						}
					} else {
						// Cat's turn - can move to any of the neighbors except hole
						for _, neighbor := range graph[catPosn] {
							if neighbor != 0 { // Can't move to hole
								childState := states[neighbor][catPosn][0] // Mouse's turn next
								currentState.children = append(currentState.children, childState)
								childState.parents = append(childState.parents, currentState)
							}
						}
					}
				}
			}
		}
	}

	// Next, a map that determines if the mouse or cat wins from this state
	mouseWins := make(map[*state]bool) // True if mouse wins from this state
	catWins := make(map[*state]bool)   // True if cat wins from this state

	// Create a queue, and enqueue all terminal states
	queue := datastructures.NewQueue[*state]()
	for mousePosn := range graph {
		if mousePosn == 0 {
			// Hole - mouse wins regardless of cat position or whose turn it is
			for catPosn := range graph {
				if catPosn != 0 {
					// Cat can't go to hole
					// Mouse wins no matter whose turn it is
					mouseWins[states[mousePosn][catPosn][0]] = true
					mouseWins[states[mousePosn][catPosn][1]] = true
					queue.Enqueue(states[mousePosn][catPosn][0])
					queue.Enqueue(states[mousePosn][catPosn][1])
				}
			}
		} else {
			// All nodes where the cat is at the same position will result in a cat win regardless of whose turn it is
			catWins[states[mousePosn][mousePosn][1]] = true
			catWins[states[mousePosn][mousePosn][0]] = true
			queue.Enqueue(states[mousePosn][mousePosn][1])
			queue.Enqueue(states[mousePosn][mousePosn][0])
		}
	}

	// For each state, keep track of its win/loss/draw status
	childrenUnresolved := make(map[*state]int) // Count of how many children of this state are unresolved
	for state := range allStates {
		childrenUnresolved[state] = len(state.children) // Initially, all children are unresolved
	}

	// We are finally ready to process the queue
	for !queue.Empty() {
		// Note that ONLY terminal states will be in the queue EVER
		currentState := queue.Dequeue()
		// What states could have preceded this state?
		for _, parentState := range currentState.parents {
			childrenUnresolved[parentState]-- // We are processing one of the children of this parent state
			if _, ok := catWins[parentState]; ok {
				// Just a terminal adjacent state - nothing to do
				continue
			} else if _, ok := mouseWins[parentState]; ok {
				// Again just a terminal adjacent state - nothing to do
				continue
			} else {
				// The adjacent state is undecided
				// Depending on whose turn it is in this state, we can determine what happens in the adjacent state
				if currentState.turn == 0 {
					// Then cat goes from parent state
					if _, ok := catWins[currentState]; ok {
						// Cat wins from current state, so cat will pick this state from the previous state and win
						catWins[parentState] = true
						queue.Enqueue(parentState)
					} else if childrenUnresolved[parentState] == 0 {
						// This could only happen if all other children of this parent state are mouse wins (if any were cat wins, then this parent state would already be a cat win)
						// So the cat from the parent state can't go ANYWHERE that is a win for it
						mouseWins[parentState] = true // Cat loses from this state
						queue.Enqueue(parentState)
					}
				} else {
					// Cat's turn, so mouse's turn previously
					if _, ok := mouseWins[currentState]; ok {
						// Mouse wins from current state, so mouse will pick this state from the previous state and win
						mouseWins[parentState] = true
						queue.Enqueue(parentState)
					} else if childrenUnresolved[parentState] == 0 {
						// This could only happen if all other children of this parent state are cat wins (if any were mouse wins, then this parent state would already be a mouse win)
						// So the mouse from the parent state can't go ANYWHERE that is a win for it
						catWins[parentState] = true // Mouse loses from this state
						queue.Enqueue(parentState)
					}
				}

			}
		}
	}

	initialState := states[1][2][0] // Mouse starts at 1, cat starts at 2, mouse goes first
	if _, ok := mouseWins[initialState]; ok {
		// Mouse wins from the initial state
		return 1
	} else if _, ok := catWins[initialState]; ok {
		// Cat wins from the initial state
		return 2
	} else {
		// Neither wins from the initial state - it's a draw
		return 0
	}
}
