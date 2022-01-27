## Unit tests

Here, unit tests means quick tests scoped on a module that doesn't rely on other modules too much, in which we won't have to mock too much because there's not a lot to mock.

## Integration tests

Integration tests mean potentially slower tests scoped on a module that uses other modules, for which we will try not to mock too much in order to trust the result.

## Mocks

In both case, we'll avoid mocking when possible.
