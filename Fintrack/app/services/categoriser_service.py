import re
import math
from collections import defaultdict


MERCHANT_RULES = {
    "tesco": "Food",
    "sainsbury": "Food",
    "sainsburys": "Food",
    "asda": "Food",
    "aldi": "Food",
    "lidl": "Food",
    "morrisons": "Food",
    "waitrose": "Food",
    "co-op": "Food",
    "coop": "Food",
    "m&s food": "Food",
    "marks spencer": "Food",
    "ocado": "Food",
    "iceland": "Food",
    "greggs": "Food",
    "pret": "Food",
    "pret a manger": "Food",
    "costa": "Food",
    "starbucks": "Food",
    "mcdonalds": "Food",
    "mcdonald": "Food",
    "kfc": "Food",
    "burger king": "Food",
    "subway": "Food",
    "nandos": "Food",
    "dominos": "Food",
    "pizza hut": "Food",
    "deliveroo": "Food",
    "uber eats": "Food",
    "just eat": "Food",
    "tfl": "Transport",
    "transport for london": "Transport",
    "uber": "Transport",
    "bolt": "Transport",
    "trainline": "Transport",
    "national rail": "Transport",
    "northern rail": "Transport",
    "avanti": "Transport",
    "lner": "Transport",
    "megabus": "Transport",
    "national express": "Transport",
    "bp": "Transport",
    "shell": "Transport",
    "esso": "Transport",
    "texaco": "Transport",
    "british gas": "Bills",
    "edf": "Bills",
    "eon": "Bills",
    "e.on": "Bills",
    "octopus energy": "Bills",
    "bulb": "Bills",
    "scottish power": "Bills",
    "sse": "Bills",
    "thames water": "Bills",
    "united utilities": "Bills",
    "severn trent": "Bills",
    "anglian water": "Bills",
    "bt ": "Bills",
    "sky ": "Bills",
    "virgin media": "Bills",
    "council tax": "Bills",
    "hmrc": "Bills",
    "tv licence": "Bills",
    "tv licensing": "Bills",
    "netflix": "Entertainment",
    "disney": "Entertainment",
    "disney+": "Entertainment",
    "prime video": "Entertainment",
    "amazon prime": "Entertainment",
    "spotify": "Entertainment",
    "apple music": "Entertainment",
    "youtube": "Entertainment",
    "now tv": "Entertainment",
    "cinema": "Entertainment",
    "odeon": "Entertainment",
    "cineworld": "Entertainment",
    "vue": "Entertainment",
    "ticketmaster": "Entertainment",
    "amazon": "Shopping",
    "asos": "Shopping",
    "boohoo": "Shopping",
    "zara": "Shopping",
    "h&m": "Shopping",
    "primark": "Shopping",
    "next ": "Shopping",
    "john lewis": "Shopping",
    "argos": "Shopping",
    "ikea": "Shopping",
    "ebay": "Shopping",
    "shein": "Shopping",
    "tk maxx": "Shopping",
    "sports direct": "Shopping",
    "jd sports": "Shopping",
    "currys": "Shopping",
    "boots": "Health",
    "superdrug": "Health",
    "pharmacy": "Health",
    "gym": "Health",
    "puregym": "Health",
    "the gym": "Health",
    "david lloyd": "Health",
    "nuffield": "Health",
    "bupa": "Health",
    "dentist": "Health",
    "dental": "Health",
    "doctor": "Health",
    "gp ": "Health",
    "hospital": "Health",
    "optical": "Health",
    "specsavers": "Health",
    "apple.com": "Subscriptions",
    "google storage": "Subscriptions",
    "icloud": "Subscriptions",
    "playstation": "Subscriptions",
    "xbox": "Subscriptions",
    "nintendo": "Subscriptions",
    "dropbox": "Subscriptions",
    "adobe": "Subscriptions",
    "microsoft 365": "Subscriptions",
    "udemy": "Education",
    "coursera": "Education",
    "skillshare": "Education",
    "linkedin learning": "Education",
    "student loan": "Education",
    "university": "Education",
    "student finance": "Education",
    "salary": "Income",
    "wages": "Income",
    "payroll": "Income",
    "hmrc refund": "Income",
    "tax refund": "Income",
    "interest earned": "Income",
    "dividend": "Income",
}

# Pre-sort rules by key length descending so longer matches win
_SORTED_RULES = sorted(MERCHANT_RULES.items(), key=lambda x: len(x[0]), reverse=True)


def categorise_by_rules(description):
    if not description:
        return None

    desc_lower = description.lower().strip()

    for merchant, category in _SORTED_RULES:
        if merchant in desc_lower:
            return category

    return None


class TransactionCategoriser:

    def __init__(self):
        self.category_word_counts = defaultdict(lambda: defaultdict(int))
        self.category_doc_counts = defaultdict(int)
        self.total_docs = 0
        self.vocabulary = set()
        self.is_trained = False

    def _tokenise(self, text):
        text = text.lower().strip()
        text = re.sub(r'[^a-z0-9\s]', ' ', text)
        tokens = [t for t in text.split() if len(t) > 1]
        return tokens

    def train(self, transactions):
        self.category_word_counts = defaultdict(lambda: defaultdict(int))
        self.category_doc_counts = defaultdict(int)
        self.total_docs = 0
        self.vocabulary = set()

        for t in transactions:
            description = t.get("description", "")
            category = t.get("category", "")

            if not description or not category:
                continue

            tokens = self._tokenise(description)
            if not tokens:
                continue

            self.category_doc_counts[category] += 1
            self.total_docs += 1

            for token in tokens:
                self.category_word_counts[category][token] += 1
                self.vocabulary.add(token)

        self.is_trained = self.total_docs >= 10
        return self.is_trained

    def predict(self, description):
        if not self.is_trained:
            return None, 0.0

        tokens = self._tokenise(description)
        if not tokens:
            return None, 0.0

        vocab_size = len(self.vocabulary)
        if vocab_size == 0:
            return None, 0.0

        scores = {}

        for category in self.category_doc_counts:
            prior = math.log(self.category_doc_counts[category] / self.total_docs)
            total_words_in_cat = sum(self.category_word_counts[category].values())

            likelihood = 0
            for token in tokens:
                word_count = self.category_word_counts[category].get(token, 0)
                prob = (word_count + 1) / (total_words_in_cat + vocab_size)
                likelihood += math.log(prob)

            scores[category] = prior + likelihood

        if not scores:
            return None, 0.0

        best_category = max(scores, key=scores.get)

        max_score = max(scores.values())
        exp_scores = {}
        for cat, score in scores.items():
            exp_scores[cat] = math.exp(score - max_score)

        total = sum(exp_scores.values())
        confidence = exp_scores[best_category] / total if total > 0 else 0

        return best_category, round(confidence, 3)

    def predict_with_fallback(self, description, min_confidence=0.4):
        matched = categorise_by_rules(description)
        if matched:
            return matched, 1.0, "rule"

        if self.is_trained:
            ml_result, confidence = self.predict(description)
            if ml_result and confidence >= min_confidence:
                return ml_result, confidence, "ml"

        return "Other", 0.0, "fallback"


def build_categoriser_for_user(categorised_transactions):
    categoriser = TransactionCategoriser()
    categoriser.train(categorised_transactions)
    return categoriser


def categorise_transactions(transactions, categoriser=None):
    results = []

    for t in transactions:
        description = t.get("description", "")

        if categoriser and categoriser.is_trained:
            category, confidence, source = categoriser.predict_with_fallback(description)
        else:
            matched = categorise_by_rules(description)
            if matched:
                category = matched
                confidence = 1.0
                source = "rule"
            else:
                category = "Other"
                confidence = 0.0
                source = "fallback"

        result = dict(t)
        result["suggested_category"] = category
        result["category_confidence"] = confidence
        result["category_source"] = source

        results.append(result)

    return results