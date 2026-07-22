package findsecretword

import "testing"

func TestFindSecretWord(t *testing.T) {
	firstMaster := NewMaster("acckzz", 10, []string{"acckzz", "ccbazz", "eiowzz", "abcczz"})
	findSecretWord([]string{"acckzz", "ccbazz", "eiowzz", "abcczz"}, firstMaster)
	if firstMaster.GetString() != "You guessed the secret word correctly." {
		t.Fatalf("Error - expected 'You guessed the secret word correctly.' but got '%s'", firstMaster.GetString())
	}

	secondMaster := NewMaster("hamada", 10, []string{"hamada", "khaled"})
	findSecretWord([]string{"hamada", "khaled"}, secondMaster)
	if secondMaster.GetString() != "You guessed the secret word correctly." {
		t.Fatalf("Error - expected 'You guessed the secret word correctly.' but got '%s'", secondMaster.GetString())
	}
}
