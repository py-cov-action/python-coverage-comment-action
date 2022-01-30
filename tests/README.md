# Test suite

## Unit tests

Here, unit tests means quick tests scoped on a module that doesn't rely on other modules too much, in which we usually won't have to mock too much because there's not a lot to mock.

## Integration tests

Integration tests mean potentially slower tests scoped on a module that uses other modules, for which we will try not to mock too much in order to trust the result.

## Mocks

In both case, we'll avoid mocking when possible.

## Caveats

The test suite does some disk operations, but we've avoided doing real networking. This means we don't test that we're using the github API correctly, we only test that we're calling it as intended. Calling the real GitHub API in the test suite would probably be much harder.

## Coverage

We currently have 100% coverage, in 3 categories:
- Low-level functions that have a lot of complex logic are unit-tested
- Glue functions have slightly less logic, there's about a dozen of possible code paths through those functions. Each path has an integration test. Any additional logic is pushed down the stack where it will be unit-tested. In order for this to work elegently, all the glue function recieve and use objects that will ultimately be responsible for the low-level behaviour that we want to be able to simulate in the test. For example, the glue functions receive an httpx Client as parameter. In the test, we're able to call these functions with test double that will not do real HTTP calls. This means that the integration tests that provide coverage for the glue functions also lets us check that the different bricks are correctly plugged to one another
- The top-level code that is responsible to call the glue functions with the real implementations for httpx clients etc. relies on mocks. It's not very elegant but it's a single function, and it means we get to have 100% coverage.

## Feedback

If you've read all the way through this point, and you have some feedback, I'd love to hear it! Either open an issue or ping me on [twitter](https://twitter.com/Ewjoachim).
