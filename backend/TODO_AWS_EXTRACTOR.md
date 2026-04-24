# TODO: Add AWS Cost Explorer extractor

This is a placeholder for issue #2.

## Implementation Plan

1. Create `extractors/aws_cost.py` following `azure_cost.py` pattern
2. Add `AWSConfig` models in `config/schema.py`
3. Add `ask_aws()` function to `config/wizard.py`
4. Add `boto3` dependency
5. Add `aws_cost` entrypoint
6. Add tests in `tests/test_aws_extractor.py`
