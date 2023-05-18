# 0x03. Unittests and Integration Tests

Unit testing is the process of testing that a particular function returns expected results for different set of inputs. A unit test is supposed to test standard inputs and corner cases. A unit test should only test the logic defined inside the tested function. Most calls to additional functions should be mocked, especially if they make network or database calls.

The goal of a unit test is to answer the question: if everything defined outside this function works as expected, does this function work as expected?

Integration tests aim to test a code path end-to-end. In general, only low level functions that make external calls such as HTTP requests, file I/O, database I/O, etc. are mocked.

Integration tests will test interactions between every part of your code.

# Resources
Read or watch:

- [unittest — Unit testing framework](https://intranet.alxswe.com/rltoken/a_AEObGK8jeqPtTPmm-gIA)
- [unittest.mock — mock object library](https://intranet.alxswe.com/rltoken/PKetnACd7FfRiU8_kpe5EA)
- [How to mock a readonly property with mock?](https://intranet.alxswe.com/rltoken/2ueVPK1kWZuz525FvZ1v2Q)
- [parameterized](https://intranet.alxswe.com/rltoken/mI7qc3Y42aZ7GTlLXDxgEg)
- [Memoization](https://intranet.alxswe.com/rltoken/x83Hdr54q4Vax5xQ2Z3HSA)

# Learning Objectives
At the end of this project, you are expected to be able to explain to anyone, without the help of Google:

- The difference between unit and integration tests.
- Common testing patterns such as mocking, parametrizations and fixtures

# Required Files
utils.py [(or download)](https://intranet-projects-files.s3.amazonaws.com/webstack/utils.py)
Click to show/hide file contents
client.py [(or download)](https://intranet-projects-files.s3.amazonaws.com/webstack/client.py)
Click to show/hide file contents
fixtures.py [(or download)](https://intranet-projects-files.s3.amazonaws.com/webstack/fixtures.py)
Click to show/hide file contents

# Tasks
# 0. Parameterize a unit test
- Familiarize yourself with the utils.access_nested_map function and understand its purpose. Play with it in the Python console to make sure you understand.

# 1. Parameterize a unit test
- Implement TestAccessNestedMap.test_access_nested_map_exception. Use the assertRaises context manager to test that a KeyError is raised for the following inputs (use @parameterized.expand):

# 2. Mock HTTP calls
- Familiarize yourself with the utils.get_json function.

Define the TestGetJson(unittest.TestCase) class and implement the TestGetJson.test_get_json method to test that utils.get_json returns the expected result.

# 3. Parameterize and patch
- Read about memoization and familiarize yourself with the utils.memoize decorator.

- Implement the TestMemoize(unittest.TestCase) class with a test_memoize method.

# 4. Parameterize and patch as decorators
- Familiarize yourself with the client.GithubOrgClient class.

In a new test_client.py file, declare the TestGithubOrgClient(unittest.TestCase) class and implement the test_org method.

# 5. Mocking a property
- memoize turns methods into properties. Read up on how to mock a property (see resource).

Implement the test_public_repos_url method to unit-test GithubOrgClient._public_repos_url.

Use patch as a context manager to patch GithubOrgClient.org and make it return a known payload.

# 6. More patching
- Implement TestGithubOrgClient.test_public_repos to unit-test GithubOrgClient.public_repos.

- Use @patch as a decorator to mock get_json and make it return a payload of your choice.

- Use patch as a context manager to mock GithubOrgClient._public_repos_url and return a value of your choice.

- Test that the list of repos is what you expect from the chosen payload.

# 7. Parameterize
- Implement TestGithubOrgClient.test_has_license to unit-test GithubOrgClient.has_license.

- Parametrize the test with the following inputs

# 8. Integration test: fixtures
- We want to test the GithubOrgClient.public_repos method in an integration test. That means that we will only mock code that sends external requests.

# AUTHOR
- [Simanga Mchunu](https://twitter.com/Simacoder)
