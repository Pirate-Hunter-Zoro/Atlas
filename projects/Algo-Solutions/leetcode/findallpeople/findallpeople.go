package findallpeople

import (
	"algo-solutions/datastructures"
	"sort"
)

/*
You are given an integer n indicating there are n people numbered from 0 to n - 1.
You are also given a 0-indexed 2D integer array meetings where meetings[i] = [xᵢ, yᵢ, timeᵢ] indicates that person xᵢ and person yᵢ have a meeting at timeᵢ.
A person may attend multiple meetings at the same time.
Finally, you are given an integer firstPerson.

Person 0 has a secret and initially shares the secret with a person firstPerson at time 0.
This secret is then shared every time a meeting takes place with a person that has the secret.
More formally, for every meeting, if a person xᵢ has the secret at timeᵢ, then they will share the secret with person yᵢ, and vice versa.

The secrets are shared instantaneously.
That is, a person may receive the secret and share it with people in other meetings within the same time frame.

Return a list of all the people that have the secret after all the meetings have taken place.
You may return the answer in any order.

Link:
https://leetcode.com/problems/find-all-people-with-secret/description/
*/
func findAllPeople(meetings [][]int, firstPerson int) []int {
	// We must arange the meetings by time
	meetingTimes := make(map[int]map[int][]int)
	for _, meeting := range meetings {
		first := meeting[0]
		second := meeting[1]
		time := meeting[2]
		if _, ok := meetingTimes[time]; !ok {
			meetingTimes[time] = make(map[int][]int)
		}
		if _, ok := meetingTimes[time][first]; !ok {
			meetingTimes[time][first] = []int{second}
		} else {
			meetingTimes[time][first] = append(meetingTimes[time][first], second)
		}
		if _, ok := meetingTimes[time][second]; !ok {
			meetingTimes[time][second] = []int{first}
		} else {
			meetingTimes[time][second] = append(meetingTimes[time][second], first)
		}
	}

	// Order the times in which meetings occurred
	orderedTimes := []int{}
	for time := range meetingTimes {
		orderedTimes = append(orderedTimes, time)
	}
	sort.SliceStable(orderedTimes, func(i, j int) bool {
		return orderedTimes[i] < orderedTimes[j]
	})

	// Find the set of all people who know the secret
	know := make(map[int]bool) // To eventually contain the list of all indivduals who know the secret
	know[0] = true
	know[firstPerson] = true
	for _, t := range orderedTimes {
		personQueue := datastructures.NewQueue[int]()
		for p := range meetingTimes[t] {
			// For every person that had a meeting at this time, add them to the queue if they know the secret
			if _, ok := know[p]; ok {
				personQueue.Enqueue(p)
			}
		}
		// Now we add people to the know list by draining and adding to our queue per the meetings that take place
		for !personQueue.Empty() {
			p := personQueue.Dequeue()
			for _, otherP := range meetingTimes[t][p] {
				// If this other person did not previously know the secret, and they do now, they need to be added to the queue for further processing
				if _, ok := know[otherP]; !ok {
					know[otherP] = true
					personQueue.Enqueue(otherP)
				}
			}
		}
	}

	// Turn the know people into a list of people to sort
	knowList := []int{}
	for p := range know {
		knowList = append(knowList, p)
	}
	sort.SliceStable(knowList, func(i int, j int) bool {
		return knowList[i] < knowList[j]
	})
	return knowList
}
