# Login Success Benchmark

## Page URL
https://global.lianlianpay.com/signin

## Credentials
- identifier_env: LOGIN_USERNAME
- password_env: LOGIN_PASSWORD
- note: For local private runs, you can add `identifier` / `password` directly to your own requirement copy
- note: If the requirement does not include plaintext credentials, the runner falls back to `.env`
- note: Official benchmark files in the repository keep placeholders only

## Goal
Verify that a user can submit valid credentials and stop immediately after the success signal appears.

## Execution Boundary
- Open the login page only
- Fill the identifier and password fields
- Submit the login form
- If MFA is required, wait for manual completion
- Stop immediately after the `LianLian` success signal is visible
- Do not navigate beyond the login success boundary

## Acceptance Criteria
1. The login page loads and displays the identifier field, password field, and submit button.
2. Valid credentials can be submitted successfully.
3. Manual verification can be waited for, but not bypassed automatically.
4. The `LianLian` success signal is treated as the end-of-test success condition.
