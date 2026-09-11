from .apis import search_words

apis = [
    ('/api/search', search_words, ['GET', 'POST']),
]
