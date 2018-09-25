## Test Setup
The tests for this app utilizes the test rig and test runners available in the tk-core repository.
The app depends on external frameworks, and these must be present in your setup in order to
execute the tests. You need the `tk-framework-widget` and `tk-framework-shotgunutils` frameworks.

The app and framework repositories need to be located at the same level on disk in order for the
test runner to find them, for example:

```
Users
  \-john.smith
      \-git
          |-tk-multi-breakdown
          |-tk-framework-shotgunutils
          \-tk-framework-widget
```

## Running the tests
Navigate to the `tests` folder in the tk-core repo, and execute the test runner. Point it
at the location of this app:

```
cd /path/to/tk-core/tests
./run_tests.sh --test-root=/path/to/tk-multi-breakdown/tests
```

alternatively, to run it directly:

```
cd /path/to/tk-multi-breakdown
/path/to/tk-core/tests/run_tests.sh --test-root=./tests
```
