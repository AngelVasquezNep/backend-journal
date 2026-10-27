# Operator Admin Provisioning CLI Contract

**Owner**: Identity | **Command**: `taskify-admin create`
**Contract version**: 1.0.0

The authorized platform operator runs this command inside the Identity environment using its
service-owned database configuration. It is not an application role or public HTTP route.
The CLI calls Identity's provisioning application use case, never ad hoc SQL or another service's
database. It uses the same input validators and Argon2 adapter as the service.

## Inputs

```text
taskify-admin create --company-name COMPANY --display-name NAME --email EMAIL
taskify-admin create --company-id UUID --display-name NAME --email EMAIL
```

Exactly one company selector is required. `--company-name` creates a company with its first admin
in one transaction. `--company-id` must identify an existing company and creates an additional
admin there. Company names need not be globally unique; identifiers distinguish them.

- Company/display names: trimmed 1–100 characters, no controls.
- Email: valid address <=254 characters, globally unique ignoring case.
- Initial password: prompted twice through hidden input, 12–128 characters without trimming.
- Optional `--password-stdin` reads one password line from a protected pipe rather than prompting;
  remove only the line terminator, not other whitespace. Do not provide a password argument,
  environment echo, shell history entry, or stdout/stderr echo.

Successful provisioning sets `role=admin` and `must_change_password=true`. Invalid input, unknown
company or duplicate email makes no changes, including no orphan company. Passwords never appear
in exceptions or normal logs. Execution is operator-authorized through access to the service
runtime and credentials; neither admins nor users receive a browser invocation capability.

## Output and exit status

On success, stdout is a single JSON object:

```json
{
  "company_id": "6c93d8dc-9b92-4dc4-bf3f-a4b48f99d9b4",
  "admin_id": "8c0f96ad-3e42-48fa-ae42-53298cf2d26b",
  "role": "admin",
  "must_change_password": true,
  "company_created": true
}
```

`company_created=false` for an additional admin. Output includes no initial password or token.
Safe diagnostics go to stderr. Exit codes: 0 success; 2 validation/usage; 3 email unavailable;
4 company not found; 5 storage/configuration failure. Repeating a successful command with the same
email returns 3 and does not create a duplicate. Automation must check exit status before using IDs.

`--help` documents fields, bounds, examples, password handling, and exit codes without a provider
API key or database connection. No update/delete/admin promotion commands are part of this feature.

## Validation evidence

Verify new-company admin, additional admin, first-login password change, duplicate email with
rollback, malformed UUID/name/email/password, and failure with unavailable storage. Assert no
password appears in process arguments, stdout/stderr, or captured application logs. Existing
companies and accounts must remain unchanged after every rejected invocation.
