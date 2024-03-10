POSITIVE_EMOJIS = {"👍", "❤", "🔥", "❤‍🔥", "😁", "🤣"}
NEGATIVE_EMOJIS = {"👎", "🤡", "💩"}


def get_reaction_change(old_reaction, new_reaction):
    # Convert reactions to sets for easier comparison
    old_set = set([reaction.emoji for reaction in old_reaction])
    new_set = set([reaction.emoji for reaction in new_reaction])

    # Determine the difference
    added = new_set - old_set

    # Check if the change is positive or negative
    for emoji in added:
        if emoji in POSITIVE_EMOJIS:
            return "positive"
        elif emoji in NEGATIVE_EMOJIS:
            return "negative"
