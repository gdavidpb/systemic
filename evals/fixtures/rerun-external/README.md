# Orders module

The public HTTP façade validates payload shape then delegates to the external refund-service.

## Business contract
Only a paid order may be refunded; shipped, cancelled and draft orders must be rejected. This repo does not include the refund-service implementation, schema, deployment configuration or its tests. This review is of the HTTP façade only.

## Change since earlier review
The old local refunds.py implementation was removed and replaced with the external RPC. No evidence about the external service status guard is available in this checkout.
